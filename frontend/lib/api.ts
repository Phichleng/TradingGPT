export async function analyze(market: string, timeframe = "15m") {
  const r = await fetch("/v1/analyze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ market, timeframe }),
  });
  return r.json();
}
