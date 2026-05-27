const REPO = "strawbo/lake-sammamish"
const WORKFLOW = "refresh_all.yml"
const REF = "main"

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "authorization, x-refresh-secret",
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

  const triggeredAt = new Date().toISOString()

  const resp = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`,
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
    const body = await resp.text()
    return new Response(JSON.stringify({ error: "GitHub trigger failed", detail: body }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    })
  }

  return new Response(JSON.stringify({ triggered: true, triggeredAt }), {
    headers: { "Content-Type": "application/json" },
  })
})
