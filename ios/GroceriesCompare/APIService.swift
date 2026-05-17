import Foundation

class APIService: NSObject, ObservableObject, URLSessionWebSocketDelegate {
    static let shared = APIService()

    var baseURL: String {
        UserDefaults.standard.string(forKey: "api_base_url") ?? "http://localhost:8000"
    }

    private var wsTask: URLSessionWebSocketTask?

    // MARK: - Start job

    func startComparison(groceryList: String, pincode: String) async throws -> String {
        guard let url = URL(string: "\(baseURL)/compare") else { throw APIError.invalidURL }
        var request = URLRequest(url: url, timeoutInterval: 30)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(
            CompareRequest(grocery_list: groceryList, pincode: pincode)
        )
        let (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw APIError.serverError(http.statusCode)
        }
        let json = try JSONDecoder().decode([String: String].self, from: data)
        guard let jobId = json["job_id"] else { throw APIError.noJobId }
        return jobId
    }

    // MARK: - WebSocket real-time progress

    func streamProgress(
        jobId: String,
        onProgress: @escaping ([String: String]) -> Void,
        onDone: @escaping (CompareResult) -> Void,
        onError: @escaping (String) -> Void
    ) {
        let wsBase = baseURL.replacingOccurrences(of: "http://", with: "ws://")
                            .replacingOccurrences(of: "https://", with: "wss://")
        guard let url = URL(string: "\(wsBase)/ws/\(jobId)") else {
            onError("Invalid WebSocket URL")
            return
        }
        let session = URLSession(configuration: .default, delegate: self, delegateQueue: .main)
        wsTask = session.webSocketTask(with: url)
        wsTask?.resume()
        receiveLoop(onProgress: onProgress, onDone: onDone, onError: onError)
    }

    private func receiveLoop(
        onProgress: @escaping ([String: String]) -> Void,
        onDone: @escaping (CompareResult) -> Void,
        onError: @escaping (String) -> Void
    ) {
        wsTask?.receive { [weak self] result in
            switch result {
            case .failure(let err):
                onError(err.localizedDescription)
            case .success(let msg):
                switch msg {
                case .string(let text):
                    guard let data = text.data(using: .utf8),
                          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                    else { break }

                    let event = json["event"] as? String ?? ""
                    if event == "progress", let progress = json["progress"] as? [String: String] {
                        DispatchQueue.main.async { onProgress(progress) }
                    } else if event == "done",
                              let resultData = try? JSONSerialization.data(withJSONObject: json["result"] as Any),
                              let compareResult = try? JSONDecoder().decode(CompareResult.self, from: resultData) {
                        DispatchQueue.main.async { onDone(compareResult) }
                        return
                    } else if event == "failed" {
                        DispatchQueue.main.async { onError("Server reported failure") }
                        return
                    }
                case .data:
                    break
                @unknown default:
                    break
                }
                self?.receiveLoop(onProgress: onProgress, onDone: onDone, onError: onError)
            }
        }
    }

    func cancelStream() { wsTask?.cancel(); wsTask = nil }

    // MARK: - Polling fallback (used if WebSocket fails)

    func pollUntilDone(
        jobId: String,
        onProgress: @escaping ([String: String]) -> Void
    ) async throws -> CompareResult {
        for _ in 0..<120 {
            guard let url = URL(string: "\(baseURL)/compare/\(jobId)") else { throw APIError.invalidURL }
            let (data, _) = try await URLSession.shared.data(from: url)
            let status = try JSONDecoder().decode(JobStatusResponse.self, from: data)
            if let progress = status.progress {
                await MainActor.run { onProgress(progress) }
            }
            if status.status == "done", let result = status.result { return result }
            if status.status == "failed" { throw APIError.jobFailed(status.error ?? "Unknown") }
            try await Task.sleep(nanoseconds: 2_000_000_000)
        }
        throw APIError.timeout
    }
}

enum APIError: LocalizedError {
    case invalidURL, noJobId, serverError(Int), jobFailed(String), timeout

    var errorDescription: String? {
        switch self {
        case .invalidURL:           return "Invalid server URL. Check Settings."
        case .noJobId:              return "Server did not return a job ID."
        case .serverError(let c):   return "Server error \(c). Is the backend running?"
        case .jobFailed(let msg):   return "Comparison failed: \(msg)"
        case .timeout:              return "Timed out waiting for results."
        }
    }
}
