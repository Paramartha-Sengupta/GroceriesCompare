import SwiftUI

struct ScanProgressView: View {
    @ObservedObject var vm: CompareViewModel
    @Environment(\.dismiss) private var dismiss

    private let platforms = ["Blinkit", "Zepto", "BigBasket", "Instamart", "AmazonFresh", "Flipkart Minutes"]

    var body: some View {
        Group {
            if let result = vm.result {
                ResultsView(result: result)
            } else if let error = vm.error {
                errorView(error)
            } else {
                scanningView
            }
        }
        .navigationBarBackButtonHidden(vm.isLoading)
        .navigationTitle(vm.isLoading ? "Scanning..." : "")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if vm.isLoading {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        vm.cancel()
                        dismiss()
                    }
                    .foregroundStyle(.red)
                }
            }
        }
    }

    private var scanningView: some View {
        VStack(spacing: 0) {
            // Progress ring
            ZStack {
                Circle()
                    .stroke(.quaternary, lineWidth: 6)
                Circle()
                    .trim(from: 0, to: Double(vm.scannedCount) / 6.0)
                    .stroke(Color.green, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeInOut, value: vm.scannedCount)
                VStack(spacing: 2) {
                    Text("\(vm.scannedCount)")
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                    Text("of 6")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 100, height: 100)
            .padding(.top, 40)

            Text(vm.statusMessage)
                .font(.headline)
                .multilineTextAlignment(.center)
                .padding(.top, 16)
                .padding(.horizontal)

            Text("Searching for the best prices across all apps in parallel")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.top, 4)
                .padding(.horizontal)

            // Platform rows
            VStack(spacing: 10) {
                ForEach(platforms, id: \.self) { platform in
                    PlatformStatusRow(
                        platform: platform,
                        status: vm.platformProgress[platform]
                    )
                }
            }
            .padding(.horizontal)
            .padding(.top, 32)

            Spacer()
        }
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 20) {
            Image(systemName: "wifi.exclamationmark")
                .font(.system(size: 52))
                .foregroundStyle(.orange)
            Text("Comparison Failed")
                .font(.title2.bold())
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            Button("Try Again") { dismiss() }
                .buttonStyle(.borderedProminent)
                .tint(.green)
        }
        .padding()
    }
}

struct PlatformStatusRow: View {
    let platform: String
    let status: String?

    private var isDone:    Bool { status == "done" }
    private var isActive:  Bool { status == "scraping" || status == nil }
    private var isError:   Bool { status?.hasPrefix("error") == true }

    var body: some View {
        HStack(spacing: 12) {
            // Platform color dot
            Circle()
                .fill(platformColors[platform] ?? .secondary)
                .frame(width: 8, height: 8)

            Image(systemName: platformIcons[platform] ?? "cart")
                .foregroundStyle(platformColors[platform] ?? .secondary)
                .frame(width: 20)

            Text(platform)
                .font(.subheadline)

            Spacer()

            if isDone {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .transition(.scale.combined(with: .opacity))
            } else if isError {
                Image(systemName: "xmark.circle.fill")
                    .foregroundStyle(.red)
            } else {
                ProgressView()
                    .scaleEffect(0.8)
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 14)
        .background(
            isDone
                ? Color.green.opacity(0.07)
                : Color(.secondarySystemBackground),
            in: RoundedRectangle(cornerRadius: 10)
        )
        .animation(.easeInOut(duration: 0.3), value: status)
    }
}
