import Foundation
import SwiftUI

// MARK: - Network models

struct CompareRequest: Encodable {
    let grocery_list: String
    let pincode: String
}

struct ItemPrice: Decodable, Identifiable {
    var id: String { platform }
    let platform: String
    let name: String
    let price: Double
    let unit: String
}

struct PriceRow: Decodable, Identifiable {
    var id: String { query }
    let query: String
    let prices: [ItemPrice]
    let cheapest_platform: String?
}

struct CartSummary: Decodable, Identifiable {
    var id: String { platform }
    let platform: String
    let item_count: Int
    let subtotal: Double
    let delivery_fee: Double
    let total: Double
    let items: [String]
}

struct CompareResult: Decodable {
    let job_id: String
    let price_matrix: [PriceRow]
    let recommended_carts: [CartSummary]
    let single_best_cart: CartSummary?
    let total_savings: Double
    let savings_pct: Double
    let unmatched_items: [String]
}

struct JobStatusResponse: Decodable {
    let status: String
    let progress: [String: String]?
    let result: CompareResult?
    let error: String?
}

// MARK: - Platform metadata

let platformColors: [String: Color] = [
    "Blinkit":          Color(hex: "#F7C900"),
    "Zepto":            Color(hex: "#8B2FC9"),
    "BigBasket":        Color(hex: "#84C225"),
    "Instamart":        Color(hex: "#FC8019"),
    "AmazonFresh":      Color(hex: "#146EB4"),
    "Flipkart Minutes": Color(hex: "#2874F0"),
]

let platformIcons: [String: String] = [
    "Blinkit":          "bolt.fill",
    "Zepto":            "hare.fill",
    "BigBasket":        "basket.fill",
    "Instamart":        "flame.fill",
    "AmazonFresh":      "leaf.fill",
    "Flipkart Minutes": "clock.fill",
]

// MARK: - Color helper

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        self.init(
            red:   Double((int >> 16) & 0xFF) / 255,
            green: Double((int >> 8)  & 0xFF) / 255,
            blue:  Double(int & 0xFF)          / 255
        )
    }
}
