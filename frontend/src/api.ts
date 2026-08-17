import type { DemoGenerateResponse, PromptTemplateResponse, Product, RunPipelineResponse } from "./types"

const API_BASE = import.meta.env.VITE_API_BASE ?? ""

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`Request failed (${res.status}): ${text}`)
  }
  return res.json() as Promise<T>
}

export function toAssetUrl(path: string | null | undefined): string {
  if (!path) return ""
  if (path.startsWith("http")) return path
  return `${API_BASE}${path}`
}

export async function runPipeline(targetCount: number, maxCandidates: number): Promise<RunPipelineResponse> {
  const res = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_count: targetCount, max_candidates: maxCandidates }),
  })
  return handle<RunPipelineResponse>(res)
}

export async function fetchProducts(): Promise<Product[]> {
  const res = await fetch(`${API_BASE}/api/products`)
  return handle<Product[]>(res)
}

export async function fetchPromptTemplate(productId: string): Promise<PromptTemplateResponse> {
  const res = await fetch(`${API_BASE}/api/demo/prompt-template?product_id=${encodeURIComponent(productId)}`)
  return handle<PromptTemplateResponse>(res)
}

export async function generateDemoComposite(
  frontageFile: File,
  productId: string,
  prompt: string,
): Promise<DemoGenerateResponse> {
  const formData = new FormData()
  formData.append("frontage", frontageFile)
  formData.append("product_id", productId)
  formData.append("prompt", prompt)

  const res = await fetch(`${API_BASE}/api/demo/generate`, {
    method: "POST",
    body: formData,
  })
  return handle<DemoGenerateResponse>(res)
}
