def calculate_quote(rd_hours: float, rd_rate: float, print_hours: float, weight_grams: float, post_processing_hours: float) -> dict:
    rd_cost = rd_hours * rd_rate
    print_cost = print_hours * 2.0
    material_cost = weight_grams * 0.08
    post_cost = post_processing_hours * 45.0
    total = rd_cost + print_cost + material_cost + post_cost
    return {
        "rd_cost": rd_cost,
        "print_cost": print_cost,
        "material_cost": material_cost,
        "post_cost": post_cost,
        "total": total
    }

if __name__ == "__main__":
    print("--- Harty Prints Quote Calculator ---")
    rd_h = float(input("R&D / Design Hours: "))
    rd_r = float(input("R&D Hourly Rate ($): "))
    print_h = float(input("Print Hours: "))
    weight = float(input("Model Weight (g): "))
    pp_h = float(input("Post Processing Hours: "))
    
    breakdown = calculate_quote(rd_h, rd_r, print_h, weight, pp_h)
    
    print("\n--- Quote Breakdown ---")
    print(f"R&D Cost: ${breakdown['rd_cost']:.2f}")
    print(f"Print Time Cost: ${breakdown['print_cost']:.2f}")
    print(f"Material Cost: ${breakdown['material_cost']:.2f}")
    print(f"Post Processing Cost: ${breakdown['post_cost']:.2f}")
    print(f"Total Quote (Q): ${breakdown['total']:.2f}")
