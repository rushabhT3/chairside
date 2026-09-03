function "price/median_cents" {
  description = "Median of an integer array of cents (sorted ascending, middle element; even counts take the lower middle so the result stays an integer)"
  input {
    int[] values
  }
  stack {
    precondition (($input.values|count) > 0) {
      error_type = "inputerror"
      error = "values must not be empty"
    }
    var $sorted { value = $input.values|sort:"":"number":false }
    var $middle { value = (($sorted|count) - 1) / 2 }
    var $median { value = $sorted|get:($middle|floor) }
  }
  response = $median
}
