/**
 * Text normalization utilities for PDF snippet matching
 */

export function normalizeText(text: string): string {
  if (!text) return ''

  let normalized = text
  normalized = normalized.replace(/-\s*\n\s*/g, '')
  normalized = normalized.replace(/\s+/g, ' ')
  normalized = normalized.normalize('NFC')
  normalized = normalized.toLowerCase()
  normalized = normalized.trim()

  return normalized
}

export function findNormalizedSnippet(
  fullText: string,
  snippet: string
): number {
  const normalizedText = normalizeText(fullText)
  const normalizedSnippet = normalizeText(snippet)
  return normalizedText.indexOf(normalizedSnippet)
}

export function containsNormalizedSnippet(
  fullText: string,
  snippet: string
): boolean {
  return findNormalizedSnippet(fullText, snippet) !== -1
}

export function extractMatchingSegment(
  fullText: string,
  snippet: string
): { start: number; end: number; text: string } | null {
  const normalizedText = normalizeText(fullText)
  const normalizedSnippet = normalizeText(snippet)

  const index = normalizedText.indexOf(normalizedSnippet)
  if (index === -1) return null

  return {
    start: index,
    end: index + normalizedSnippet.length,
    text: fullText.slice(index, index + snippet.length),
  }
}
