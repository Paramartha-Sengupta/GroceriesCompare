import Foundation
import SwiftUI

@MainActor
class CompareViewModel: ObservableObject {
    @Published var isLoading = false
    @Published var result: CompareResult?
    @Published var error: String?
    @Published var statusMessage = "Starting comparison..."
    @Published var platformProgress: [String: String] = [:]
    @Published var scannedCount = 0

    private let allPlatforms = ["Blinkit", "Zepto", "BigBasket", "Instamart", "AmazonFresh", "Flipkart Minutes"]

    func compare(groceryText: String, pincode: String) async {
        isLoading = true
        result = nil
        error = nil
        platformProgress = [:]
        scannedCount = 0
        statusMessage = "Normalizing your list..."

        do {
            let jobId = try await APIService.shared.startComparison(
                groceryList: groceryText,
                pincode: pincode
            )
            statusMessage = "Scanning 6 apps simultaneously..."
            await withCheckedContinuation { continuation in
                APIService.shared.streamProgress(
                    jobId: jobId,
                    onProgress: { [weak self] progress in
                        guard let self else { return }
                        self.platformProgress = progress
                        let done = progress.values.filter { $0 == "done" }.count
                        self.scannedCount = done
                        self.statusMessage = done < 6 ? "Scanned \(done) of 6 apps..." : "Crunching numbers..."
                    },
                    onDone: { [weak self] compareResult in
                        self?.result = compareResult
                        self?.isLoading = false
                        continuation.resume()
                    },
                    onError: { [weak self] _ in
                        // WebSocket failed — fall through to polling
                        continuation.resume()
                    }
                )
            }

            // If WebSocket didn't deliver a result, fall back to polling
            if result == nil && isLoading {
                let compareResult = try await APIService.shared.pollUntilDone(jobId: jobId) { [weak self] progress in
                    guard let self else { return }
                    self.platformProgress = progress
                    let done = progress.values.filter { $0 == "done" }.count
                    self.scannedCount = done
                    self.statusMessage = "Scanned \(done) of 6 apps..."
                }
                result = compareResult
            }
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    func cancel() {
        APIService.shared.cancelStream()
        isLoading = false
    }
}
