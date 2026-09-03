mcp_server "chairside-mcp" {
  canonical = "chairside-mcp"
  description = "Tools other agents can call: book a chair, read a consultation summary, check a price. Every tool requires a user token; the Cloudflare Worker in worker-oauth/ fronts this server with OAuth 2.1 for Claude Web and ChatGPT."
  instructions = """
    Chairside salon tools.
    - book_appointment: book a chair for the authenticated user (needs salon, service, when).
    - get_consultation_summary: what the last consultation recommended and where it stands.
    - price_check: salon price beside the market spread for a catalog product.
    All tools act as the authenticated user; clients only ever see their own records.
  """
  tags = ["chairside", "salon", "booking"]
  tools = [
    { name: "book_appointment", auth: "user" },
    { name: "get_consultation_summary", auth: "user" },
    { name: "price_check", auth: "user" }
  ]
  guid = "6PWdQdI9gvVogX5nmJS8hHT18j0"
}
