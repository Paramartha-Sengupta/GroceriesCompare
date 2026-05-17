import SwiftUI

struct GroceryListInputView: View {
    @StateObject private var vm = CompareViewModel()
    @State private var groceryText = ""
    @State private var pincode = UserDefaults.standard.string(forKey: "saved_pincode") ?? ""
    @State private var showingResults = false
    @State private var showingSettings = false

    var canCompare: Bool {
        !groceryText.trimmingCharacters(in: .whitespaces).isEmpty && pincode.count == 6
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {

                    // Header
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("GroceriesCompare")
                                .font(.largeTitle.bold())
                            Text("Find the cheapest cart across 6 apps")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button { showingSettings = true } label: {
                            Image(systemName: "gearshape")
                                .font(.title3)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.top, 8)

                    // Platform pills
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(["Blinkit", "Zepto", "BigBasket", "Instamart", "AmazonFresh", "Flipkart Minutes"], id: \.self) { p in
                                Label(p, systemImage: platformIcons[p] ?? "cart")
                                    .font(.caption2.bold())
                                    .foregroundStyle(platformColors[p] ?? .primary)
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 5)
                                    .background((platformColors[p] ?? .primary).opacity(0.12), in: Capsule())
                            }
                        }
                    }

                    // Pincode
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Delivery Pincode", systemImage: "location.fill")
                            .font(.headline)
                        HStack {
                            TextField("6-digit pincode", text: $pincode)
                                .keyboardType(.numberPad)
                                .onChange(of: pincode) { _, new in
                                    if new.count > 6 { pincode = String(new.prefix(6)) }
                                    UserDefaults.standard.set(pincode, forKey: "saved_pincode")
                                }
                            if pincode.count == 6 {
                                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                            }
                        }
                        .padding(12)
                        .background(.quaternary, in: RoundedRectangle(cornerRadius: 10))
                    }

                    // Grocery list
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Label("Your Grocery List", systemImage: "list.bullet")
                                .font(.headline)
                            Spacer()
                            if !groceryText.isEmpty {
                                Button("Clear") { groceryText = "" }
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Text("One item per line or comma-separated. Include brand and quantity.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        TextEditor(text: $groceryText)
                            .frame(minHeight: 180)
                            .padding(8)
                            .background(.quaternary, in: RoundedRectangle(cornerRadius: 10))
                            .overlay(RoundedRectangle(cornerRadius: 10).stroke(.quaternary, lineWidth: 1))
                    }

                    // Quick-fill examples
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Try an example:")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(exampleLists, id: \.title) { ex in
                                    Button(ex.title) { groceryText = ex.list }
                                        .buttonStyle(.bordered)
                                        .font(.caption)
                                        .tint(.secondary)
                                }
                            }
                        }
                    }

                    // Compare button
                    Button {
                        showingResults = true
                        Task { await vm.compare(groceryText: groceryText, pincode: pincode) }
                    } label: {
                        HStack {
                            Image(systemName: "magnifyingglass")
                            Text("Compare Prices Now")
                                .fontWeight(.semibold)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 6)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .disabled(!canCompare)
                    .tint(.green)
                }
                .padding(.horizontal)
                .padding(.bottom, 24)
            }
            .navigationBarHidden(true)
            .navigationDestination(isPresented: $showingResults) {
                ScanProgressView(vm: vm)
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView()
            }
        }
    }

    private let exampleLists: [(title: String, list: String)] = [
        ("Weekly basics",    "2L milk, eggs 12, amul butter 500g, bread, atta 5kg"),
        ("Veggies",          "tomatoes 1kg, onions 2kg, potatoes 2kg, capsicum"),
        ("Pantry restock",   "sugar 1kg, salt, oil 1L, dal 500g, rice 5kg"),
    ]
}

// MARK: - Settings

struct SettingsView: View {
    @Environment(\.dismiss) var dismiss
    @State private var serverURL = UserDefaults.standard.string(forKey: "api_base_url") ?? "http://localhost:8000"

    var body: some View {
        NavigationStack {
            Form {
                Section("Backend Server") {
                    TextField("http://localhost:8000", text: $serverURL)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                }
                Section {
                    Text("Point this to your Railway URL after deploying the backend. Keep localhost:8000 for local testing.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        UserDefaults.standard.set(serverURL, forKey: "api_base_url")
                        dismiss()
                    }
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
