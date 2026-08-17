export type VenueType = "cafe" | "restaurant" | "salon" | "other"

export interface VenueCandidate {
  venue_id: string
  name: string
  address: string | null
  postcode: string | null
  lat: number
  lng: number
  venue_type: VenueType
  osm_tags: Record<string, string>
  website: string | null
  osm_photo_url: string | null
}

export interface FitVerdict {
  accepted: boolean
  score: number
  reasoning: string
  signals: Record<string, string>
}

export interface ScoredVenue {
  venue: VenueCandidate
  fit: FitVerdict
}

export interface FrontageAttempt {
  source: string
  accepted: boolean
  reasoning: string
  image_path: string | null
  heading_deg: number | null
  fov_deg: number | null
  image_ref: string | null
}

export interface FrontageResult {
  venue_id: string
  accepted: boolean
  final_source: string | null
  image_path: string | null
  image_url: string | null
  heading_deg: number | null
  fov_deg: number | null
  reasoning: string
  entrance_zoomed: boolean
  entrance_confidence: number | null
  attempts: FrontageAttempt[]
}

export interface Product {
  id: string
  name: string
  description: string
  image_path: string
  image_url: string
  reference_height_m: number
  reference_note: string
}

export interface CompositeAttempt {
  attempt_number: number
  image_path: string | null
  image_url: string | null
  accepted: boolean
  reasoning: string
  checks: Record<string, boolean>
}

export interface CompositeResult {
  venue_id: string
  product_id: string
  accepted: boolean
  method: "gemini" | "classical"
  final_image_path: string | null
  final_image_url: string | null
  reasoning: string
  scale_note: string
  attempts: CompositeAttempt[]
}

export interface VenuePipelineResult {
  venue: VenueCandidate
  fit: FitVerdict
  frontage: FrontageResult | null
  composite: CompositeResult | null
  product: Product | null
}

export interface PipelineRunResult {
  requested_count: number
  candidates_considered: number
  rejected_venues: ScoredVenue[]
  results: VenuePipelineResult[]
}

export interface RunPipelineResponse {
  run_id: string
  result: PipelineRunResult
}

export interface PromptTemplateResponse {
  product_id: string
  prompt: string
}

export interface DemoGenerateResponse {
  frontage_image_url: string
  product_id: string
  method: "gemini" | "classical"
  qa_passed: boolean
  image_url: string | null
  reasoning: string
  checks: Record<string, boolean>
  prompt_used: string | null
}
