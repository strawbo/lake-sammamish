const REPO = "strawbo/lake-sammamish"
const REF = "main"

const WORKFLOWS: Record<string, string> = {
  buoy:    "refresh_buoy.yml",
  weather: "refresh_weather.yml",
  all:     "refresh_all.yml",
}

const RUN_NAMES: Record<string, string> = {
  buoy:    "Refresh Buoy Data",
  weather: "Refresh Weather & Wind",
  all:     "Refresh All Data",
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "authorization, x-refresh-secret, content-type",
      },
    })
  }

  const secret = Deno.env.get("REFRESH_SECRET")
  if (!secret || req.headers.get("x-refresh-secret") !== secret) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    })
  }

  const githubToken = Deno.env.get("GITHUB_PAT")
  if (!githubToken) {
    return new Response(JSON.stringify({ error: "Server misconfigured" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })
  }

  let type = "all"
  try {
    const body = await req.json()
    if (body?.type && WORKFLOWS[body.type]) type = body.type
  } catch { /* no body or invalid JSON — default to "all" */ }

  const workflow = WORKFLOWS[type]
  const triggeredAt = new Date().toISOString()

  const resp = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${githubToken}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: REF }),
    }
  )

  if (resp.status !== 204) {
    const detail = await resp.text()
    return new Response(JSON.stringify({ error: "GitHub trigger failed", detail }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    })
  }

  return new Response(
    JSON.stringify({ triggered: true, type, runName: RUN_NAMES[type], triggeredAt }),
    { headers: { "Content-Type": "application/json" } }
  )
})
