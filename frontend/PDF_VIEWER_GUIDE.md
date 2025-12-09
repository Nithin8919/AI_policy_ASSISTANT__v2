# PDF Viewer - Frontend Integration Guide

## 🎯 Overview

The PDF viewer frontend is now fully implemented with:
- ✅ React-pdf integration
- ✅ Snippet highlighting
- ✅ Page navigation and zoom controls
- ✅ Loading and error states
- ✅ TypeScript support
- ✅ Responsive design

## 📦 Installation

### Step 1: Install Dependencies

```bash
cd frontend
./install_pdf_deps.sh
```

Or manually:
```bash
npm install react-pdf pdfjs-dist
```

### Step 2: Configure Environment

Add to `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🔧 Components Created

### 1. `lib/pdfViewerApi.ts`
API service for backend communication:
- `getPdfUrl(docId)` - Get signed GCS URL
- `locateSnippet(docId, snippet)` - Find page number
- `openPdfAtSnippet(docId, snippet)` - Combined function

### 2. `lib/textNormalization.ts`
Text normalization utilities (mirrors backend):
- `normalizeText(text)` - Normalize for matching
- `findNormalizedSnippet(text, snippet)` - Find snippet position
- `containsNormalizedSnippet(text, snippet)` - Check if contains

### 3. `components/PdfViewer/index.tsx`
Main PDF viewer component with:
- PDF rendering via react-pdf
- Page navigation (prev/next)
- Zoom controls (50% - 200%)
- Loading spinner
- Error handling
- Snippet highlighting

### 4. `hooks/usePdfViewer.ts`
React hook for managing PDF viewer state:
- `openWithSnippet(docId, snippet, title)` - Open with highlighting
- `openPdf(docId, title, page)` - Open without highlighting
- `closePdf()` - Close viewer
- State management (loading, error, etc.)

## 🚀 Usage Examples

### Example 1: Basic Usage with Hook

```tsx
'use client';

import { usePdfViewer } from '@/hooks/usePdfViewer';
import { PdfViewer } from '@/components/PdfViewer';
import { Button } from '@/components/ui/button';

export function MyComponent() {
  const { state, openWithSnippet, closePdf } = usePdfViewer();

  const handleCitationClick = async () => {
    await openWithSnippet(
      '2018se_ms70',  // doc_id from Qdrant
      'This is the text snippet to highlight',
      'GO MS 70 - 2018'  // Optional title
    );
  };

  return (
    <>
      <Button onClick={handleCitationClick}>
        View PDF
      </Button>

      {state.isOpen && state.pdfUrl && (
        <PdfViewer
          fileUrl={state.pdfUrl}
          initialPage={state.pageNumber || 1}
          highlightText={state.highlightText || undefined}
          title={state.title || undefined}
          onClose={closePdf}
        />
      )}
    </>
  );
}
```

### Example 2: Integration in ChatMessage Component

Add to your existing `ChatMessage.tsx`:

```tsx
import { usePdfViewer } from '@/hooks/usePdfViewer';
import { PdfViewer } from '@/components/PdfViewer';

export function ChatMessage({ message }: { message: Message }) {
  const { state, openWithSnippet, closePdf } = usePdfViewer();

  const handleCitationClick = async (citation: Citation) => {
    // citation has: docId, span (snippet text), source (title)
    await openWithSnippet(
      citation.docId,
      citation.span,
      citation.source
    );
  };

  return (
    <div>
      {/* Your existing message rendering */}
      
      {/* Citations */}
      {message.citations?.map((citation, idx) => (
        <button
          key={idx}
          onClick={() => handleCitationClick(citation)}
          className="citation-button"
        >
          [{idx + 1}] {citation.source}
        </button>
      ))}

      {/* PDF Viewer Modal */}
      {state.isOpen && state.pdfUrl && (
        <PdfViewer
          fileUrl={state.pdfUrl}
          initialPage={state.pageNumber || 1}
          highlightText={state.highlightText || undefined}
          title={state.title || undefined}
          onClose={closePdf}
        />
      )}
    </div>
  );
}
```

### Example 3: Direct API Usage (Without Hook)

```tsx
import { openPdfAtSnippet } from '@/lib/pdfViewerApi';
import { PdfViewer } from '@/components/PdfViewer';
import { useState } from 'react';

export function DirectApiExample() {
  const [pdfData, setPdfData] = useState<any>(null);

  const handleClick = async () => {
    try {
      const result = await openPdfAtSnippet(
        '2018se_ms70',
        'text snippet'
      );
      
      setPdfData(result);
    } catch (error) {
      console.error('Failed to open PDF:', error);
    }
  };

  return (
    <>
      <button onClick={handleClick}>Open PDF</button>
      
      {pdfData && (
        <PdfViewer
          fileUrl={pdfData.pdfUrl}
          initialPage={pdfData.page || 1}
          highlightText="text snippet"
          onClose={() => setPdfData(null)}
        />
      )}
    </>
  );
}
```

## 🎨 Styling

The PDF viewer uses your existing UI components:
- `Button` from `@/components/ui/button`
- Tailwind CSS classes
- Dark mode support via `dark:` classes

### Customization

To customize the viewer appearance, edit `components/PdfViewer/index.tsx`:

```tsx
// Change background
<div className="bg-gray-100 dark:bg-gray-900">

// Change header style
<div className="p-4 border-b bg-card">

// Adjust modal size
<div className="max-w-7xl max-h-[95vh]">
```

## 🔍 Advanced Features

### Custom Highlighting

The current implementation uses `customTextRenderer` for highlighting. To enhance it:

```tsx
const customTextRenderer = useCallback(
  (textItem: any) => {
    if (!highlightText) return textItem.str;

    const normalizedText = normalizeText(textItem.str);
    const normalizedHighlight = normalizeText(highlightText);

    if (normalizedText.includes(normalizedHighlight)) {
      // Return JSX for highlighted text
      return (
        <mark className="bg-yellow-200 dark:bg-yellow-600">
          {textItem.str}
        </mark>
      );
    }

    return textItem.str;
  },
  [highlightText]
);
```

### Keyboard Shortcuts

Add keyboard navigation:

```tsx
useEffect(() => {
  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft') goToPrevPage();
    if (e.key === 'ArrowRight') goToNextPage();
    if (e.key === 'Escape') onClose?.();
  };

  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, [goToPrevPage, goToNextPage, onClose]);
```

### Download PDF

Add a download button:

```tsx
const handleDownload = () => {
  const link = document.createElement('a');
  link.href = fileUrl;
  link.download = title || 'document.pdf';
  link.click();
};

// In the header controls:
<Button variant="ghost" size="sm" onClick={handleDownload}>
  <Download className="h-4 w-4" />
</Button>
```

## 🐛 Troubleshooting

### Issue: "Cannot find module 'react-pdf'"

**Solution:**
```bash
npm install react-pdf pdfjs-dist
```

### Issue: "PDF.js worker not loading"

**Solution:**
The worker is loaded from CDN. If you need local hosting:

```tsx
import { pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.js',
  import.meta.url,
).toString();
```

### Issue: "CORS error when loading PDF"

**Solution:**
Ensure GCS CORS is configured (see backend setup guide).

### Issue: "Snippet not highlighting"

**Solution:**
1. Check that normalization matches backend
2. Verify snippet text is exactly from Qdrant
3. Check browser console for errors

## 📊 Performance Tips

1. **Lazy Loading**: Only load PDF when modal opens
2. **Page Caching**: react-pdf caches rendered pages
3. **Signed URL Expiration**: URLs expire after 60 minutes (configurable)
4. **Text Layer**: Disable if not needed for better performance:
   ```tsx
   <Page renderTextLayer={false} />
   ```

## ✅ Testing Checklist

- [ ] Install dependencies (`./install_pdf_deps.sh`)
- [ ] Configure `NEXT_PUBLIC_API_URL` in `.env.local`
- [ ] Backend is running (`python main_v3.py`)
- [ ] GCS authentication is configured
- [ ] CORS is set up on GCS bucket
- [ ] Test opening a PDF from a citation
- [ ] Test page navigation (prev/next)
- [ ] Test zoom controls
- [ ] Test snippet highlighting
- [ ] Test error handling (invalid doc_id)
- [ ] Test on mobile/tablet

## 🔗 Related Files

- Backend API: `retrieval_v3/api/pdf_url.py`, `locate_snippet.py`
- Backend Services: `retrieval_v3/services/gcs_service.py`, `pdf_service.py`
- Backend Setup: `retrieval_v3/SETUP_GUIDE.md`
- Infrastructure: `retrieval_v3/infra/README.md`

## 📝 Next Steps

1. **Install dependencies** using `./install_pdf_deps.sh`
2. **Integrate into ChatMessage** component (see Example 2)
3. **Test with real citations** from your search results
4. **Customize styling** to match your design
5. **Add analytics** to track PDF viewer usage
6. **Consider caching** PDF URLs client-side

---

**Questions?** Check the backend setup guide or the inline code comments!
