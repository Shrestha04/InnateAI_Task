import { useEffect, useState } from "react"
import { fetchProducts, fetchPromptTemplate, generateDemoComposite, toAssetUrl } from "../api"
import type { DemoGenerateResponse, Product } from "../types"
import { BeforeAfter } from "./BeforeAfter"
import { StatusBadge } from "./StatusBadge"

const CHECK_LABEL: Record<string, string> = {
  building_unaltered: "Building unaltered",
  product_matches_reference: "Matches reference product",
  scale_plausible: "Scale plausible",
  perspective_plausible: "Perspective plausible",
  has_grounding_and_shadow: "Grounded with shadow",
  no_visual_artifacts: "No artifacts",
  method_classical_fallback: "Classical fallback used",
}

export function DemoPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [productId, setProductId] = useState<string>("")
  const [prompt, setPrompt] = useState("")
  const [frontageFile, setFrontageFile] = useState<File | null>(null)
  const [frontagePreview, setFrontagePreview] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [result, setResult] = useState<DemoGenerateResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProducts().then((list) => {
      setProducts(list)
      if (list.length > 0) setProductId(list[0].id)
    })
  }, [])

  useEffect(() => {
    if (!productId) return
    fetchPromptTemplate(productId).then((res) => setPrompt(res.prompt))
  }, [productId])

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null
    setFrontageFile(file)
    setResult(null)
    setError(null)
    if (file) {
      setFrontagePreview(URL.createObjectURL(file))
    } else {
      setFrontagePreview(null)
    }
  }

  async function handleResetPrompt() {
    const res = await fetchPromptTemplate(productId)
    setPrompt(res.prompt)
  }

  async function handleGenerate() {
    if (!frontageFile || !productId) return
    setIsGenerating(true)
    setError(null)
    setResult(null)
    try {
      const res = await generateDemoComposite(frontageFile, productId, prompt)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.")
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div
        className="rounded-xl border px-5 py-4 text-sm"
        style={{ borderColor: "var(--line)", background: "var(--surface)", color: "var(--ink-muted)" }}
      >
        Upload a frontage photo, pick a product, and edit the compositing prompt directly — a manual playground
        separate from the automated pipeline, for seeing exactly what a given prompt produces. Falls back to the
        classical method automatically if Gemini can't generate (see the pipeline tab for why).
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div
          className="flex flex-col gap-4 rounded-xl border p-5"
          style={{ borderColor: "var(--line)", background: "var(--surface)" }}
        >
          <div>
            <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
              Frontage photo
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="block w-full text-sm"
            />
            {frontagePreview && (
              <div className="mt-2 overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
                <img src={frontagePreview} alt="Frontage preview" className="aspect-[4/3] w-full object-cover" />
              </div>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
              Product
            </label>
            <div className="grid grid-cols-3 gap-2">
              {products.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setProductId(p.id)}
                  className="overflow-hidden rounded-lg border text-left"
                  style={{
                    borderColor: productId === p.id ? "var(--accent)" : "var(--line)",
                    borderWidth: productId === p.id ? 2 : 1,
                  }}
                >
                  <img src={toAssetUrl(p.image_url)} alt={p.name} className="aspect-square w-full object-cover" />
                  <div className="px-1.5 py-1 text-[11px] leading-tight">{p.name}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
                Compositing prompt
              </label>
              <button onClick={handleResetPrompt} className="text-xs font-medium underline" style={{ color: "var(--accent)" }}>
                Reset to default
              </button>
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={10}
              className="w-full rounded-md border p-2.5 font-mono-ui text-xs"
              style={{ borderColor: "var(--line-strong)" }}
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={!frontageFile || isGenerating}
            className="rounded-md px-4 py-2 text-sm font-semibold transition-opacity disabled:opacity-50"
            style={{ background: "var(--accent)", color: "#0a0a0b" }}
          >
            {isGenerating ? "Generating…" : "Generate composite"}
          </button>
        </div>

        <div
          className="flex flex-col gap-3 rounded-xl border p-5"
          style={{ borderColor: "var(--line)", background: "var(--surface)" }}
        >
          <h3 className="text-sm font-semibold">Result</h3>

          {error && (
            <div
              className="rounded-md border px-3 py-2 text-xs"
              style={{ borderColor: "var(--bad-soft)", background: "var(--bad-soft)", color: "var(--bad)" }}
            >
              {error}
            </div>
          )}

          {!result && !error && !isGenerating && (
            <div
              className="flex flex-1 items-center justify-center rounded-lg border border-dashed px-3 py-10 text-center text-xs"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              Upload a photo and generate to see the before/after here.
            </div>
          )}

          {isGenerating && (
            <div
              className="flex flex-1 items-center justify-center rounded-lg border px-3 py-10 text-center text-xs"
              style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
            >
              Generating…
            </div>
          )}

          {result && (
            <>
              <div className="flex items-center gap-2">
                <span
                  className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                  style={{
                    background: result.method === "classical" ? "var(--warn-soft)" : "var(--accent-soft)",
                    color: result.method === "classical" ? "var(--warn)" : "var(--accent)",
                  }}
                >
                  {result.method === "classical" ? "Classical fallback" : "Gemini generation"}
                </span>
                <StatusBadge accepted={result.qa_passed} acceptedLabel="Passed QA" rejectedLabel="Failed QA" />
              </div>

              {result.image_url && (
                <BeforeAfter
                  beforeUrl={toAssetUrl(result.frontage_image_url)}
                  afterUrl={toAssetUrl(result.image_url)}
                  downloadFileName={`demo-${result.product_id}-planters.jpg`}
                />
              )}

              <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
                {result.reasoning}
              </p>

              {Object.keys(result.checks).length > 0 && (
                <div className="grid grid-cols-2 gap-1.5">
                  {Object.entries(result.checks).map(([key, passed]) => (
                    <div
                      key={key}
                      className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px]"
                      style={{
                        borderColor: passed ? "var(--good-soft)" : "var(--bad-soft)",
                        background: passed ? "var(--good-soft)" : "var(--bad-soft)",
                        color: passed ? "var(--good)" : "var(--bad)",
                      }}
                    >
                      <span
                        className="h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ background: passed ? "var(--good)" : "var(--bad)" }}
                      />
                      {CHECK_LABEL[key] ?? key}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
