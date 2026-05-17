import SwiftUI

struct ResultsView: View {
    let result: CompareResult

    private var isSplit: Bool { result.recommended_carts.count > 1 }

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {

                // Savings banner
                if result.total_savings > 0 {
                    SavingsBanner(savings: result.total_savings, pct: result.savings_pct, isSplit: isSplit)
                } else {
                    SingleAppBanner(cart: result.single_best_cart)
                }

                // Recommended cart(s)
                SectionHeader(
                    title: isSplit ? "Optimal Split" : "Best App",
                    subtitle: isSplit ? "Buy from these \(result.recommended_carts.count) apps" : "All items cheapest here"
                )
                ForEach(result.recommended_carts) { cart in
                    CartCard(cart: cart)
                        .padding(.horizontal)
                }

                // Single-app comparison (only shown when split is recommended)
                if isSplit, let single = result.single_best_cart {
                    SectionHeader(title: "vs. One App", subtitle: "If you ordered everything from \(single.platform)")
                    CartCard(cart: single, style: .dimmed)
                        .padding(.horizontal)
                }

                Divider().padding(.horizontal)

                // Per-item matrix
                SectionHeader(title: "Item Breakdown", subtitle: "Cheapest highlighted in green")
                ForEach(result.price_matrix) { row in
                    PriceRowCard(row: row)
                        .padding(.horizontal)
                }

                // Unmatched
                if !result.unmatched_items.isEmpty {
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: "questionmark.circle.fill").foregroundStyle(.orange)
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Not found on any platform")
                                .font(.subheadline.bold())
                                .foregroundStyle(.orange)
                            ForEach(result.unmatched_items, id: \.self) {
                                Text("• \($0)").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                    .padding()
                    .background(.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal)
                }

                Spacer(minLength: 32)
            }
            .padding(.top, 16)
        }
        .navigationTitle("Results")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Subviews

struct SectionHeader: View {
    let title: String
    let subtitle: String
    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title).font(.headline)
            Text("·  \(subtitle)").font(.caption).foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.horizontal)
        .padding(.top, 4)
    }
}

struct SavingsBanner: View {
    let savings: Double; let pct: Double; let isSplit: Bool
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 6) {
                Text(isSplit ? "Split & save" : "You save")
                    .font(.subheadline).foregroundStyle(.white.opacity(0.85))
                Text("₹\(savings, specifier: "%.0f")")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(.white)
                Text("\(pct, specifier: "%.1f")% cheaper than best single app")
                    .font(.caption).foregroundStyle(.white.opacity(0.8))
            }
            Spacer()
            Image(systemName: "indianrupeesign.circle.fill")
                .font(.system(size: 52)).foregroundStyle(.white.opacity(0.3))
        }
        .padding(20)
        .background(
            LinearGradient(colors: [Color(hex: "#1a7a3f"), Color(hex: "#20a050")],
                           startPoint: .topLeading, endPoint: .bottomTrailing),
            in: RoundedRectangle(cornerRadius: 18)
        )
        .padding(.horizontal)
    }
}

struct SingleAppBanner: View {
    let cart: CartSummary?
    var body: some View {
        HStack {
            Image(systemName: "checkmark.circle.fill").foregroundStyle(.green).font(.title2)
            VStack(alignment: .leading, spacing: 2) {
                Text("Best single app")
                    .font(.subheadline).foregroundStyle(.secondary)
                Text(cart?.platform ?? "").font(.headline)
            }
            Spacer()
            Text("₹\(cart?.total ?? 0, specifier: "%.0f")").font(.title3.bold())
        }
        .padding()
        .background(Color.green.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
        .padding(.horizontal)
    }
}

enum CartCardStyle { case recommended, dimmed }

struct CartCard: View {
    let cart: CartSummary
    var style: CartCardStyle = .recommended

    private var isDimmed: Bool { style == .dimmed }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header row
            HStack {
                Image(systemName: platformIcons[cart.platform] ?? "cart")
                    .foregroundStyle(platformColors[cart.platform] ?? .secondary)
                    .font(.title3)
                Text(cart.platform).font(.headline)
                Spacer()
                VStack(alignment: .trailing, spacing: 1) {
                    Text("₹\(cart.total, specifier: "%.0f")")
                        .font(.title3.bold())
                        .foregroundStyle(isDimmed ? .secondary : .primary)
                    if cart.delivery_fee > 0 {
                        Text("incl. ₹\(cart.delivery_fee, specifier: "%.0f") delivery")
                            .font(.caption2).foregroundStyle(.orange)
                    } else {
                        Text("Free delivery").font(.caption2).foregroundStyle(.green)
                    }
                }
            }

            // Subtotal breakdown
            HStack {
                Label("\(cart.item_count) items", systemImage: "bag")
                Spacer()
                Text("Subtotal ₹\(cart.subtotal, specifier: "%.0f")")
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            // Item tags
            TagCloud(tags: cart.items)
        }
        .padding()
        .background(.background, in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14)
            .stroke(isDimmed ? Color.secondary.opacity(0.15) : Color.green.opacity(0.3), lineWidth: 1.5))
        .opacity(isDimmed ? 0.65 : 1.0)
    }
}

struct PriceRowCard: View {
    let row: PriceRow
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(row.query.capitalized).font(.subheadline.bold())
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(row.prices.sorted { $0.price < $1.price }) { p in
                        let cheapest = p.platform == row.cheapest_platform
                        VStack(spacing: 3) {
                            Text(p.platform)
                                .font(.system(size: 9, weight: .medium))
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                            Text("₹\(p.price, specifier: "%.0f")")
                                .font(.subheadline.bold())
                                .foregroundStyle(cheapest ? .green : .primary)
                            if !p.unit.isEmpty {
                                Text(p.unit)
                                    .font(.system(size: 9))
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(cheapest ? Color.green.opacity(0.1) : Color(.secondarySystemBackground),
                                    in: RoundedRectangle(cornerRadius: 10))
                        .overlay(RoundedRectangle(cornerRadius: 10)
                            .stroke(cheapest ? Color.green : .clear, lineWidth: 1.5))
                    }
                }
            }
        }
        .padding()
        .background(.background, in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(.quaternary, lineWidth: 1))
    }
}

struct TagCloud: View {
    let tags: [String]
    var body: some View {
        // Simple wrapping tag cloud using lazy VStack trick
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 80), spacing: 6)], spacing: 6) {
            ForEach(tags, id: \.self) { tag in
                Text(tag)
                    .font(.caption2)
                    .lineLimit(1)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(.quaternary, in: Capsule())
            }
        }
    }
}
