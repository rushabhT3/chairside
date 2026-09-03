function "price/delta_pct" {
  description = "Integer percentage deviation of the salon price from the market median; positive means the salon is above market"
  input {
    int salon_price_cents
    int median_cents
  }
  stack {
    precondition ($input.median_cents > 0) {
      error_type = "inputerror"
      error = "median_cents must be positive"
    }
    var $delta { value = ((($input.salon_price_cents - $input.median_cents) * 100) / $input.median_cents)|round }
  }
  response = $delta
}
