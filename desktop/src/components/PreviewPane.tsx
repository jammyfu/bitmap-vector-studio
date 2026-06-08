import React, { useState, useCallback, useRef } from 'react';

interface PreviewPaneProps {
  originalSrc?: string;
  resultSrc?: string;
  fileName?: string;
  onDownload?: () => void;
}

export const PreviewPane: React.FC<PreviewPaneProps> = ({
  originalSrc,
  resultSrc,
  fileName,
  onDownload,
}) => {
  const [mode, setMode] = useState<'side-by-side' | 'overlay'>('side-by-side');
  const [overlayPos, setOverlayPos] = useState(50);
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const zoomIn = useCallback(() => setScale((s) => Math.min(s + 0.25, 5)), []);
  const zoomOut = useCallback(() => setScale((s) => Math.max(s - 0.25, 0.25)), []);
  const zoomFit = useCallback(() => setScale(1), []);

  const handleOverlayMouseDown = useCallback(() => {
    isDragging.current = true;
  }, []);

  const handleOverlayMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setOverlayPos(pct);
    },
    []
  );

  const handleOverlayMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const hasContent = originalSrc || resultSrc;

  return (
    <div className="preview-pane">
      <div className="preview-toolbar">
        <div className="preview-modes">
          <button
            className={`preview-mode-btn ${mode === 'side-by-side' ? 'active' : ''}`}
            onClick={() => setMode('side-by-side')}
          >
            Split
          </button>
          <button
            className={`preview-mode-btn ${mode === 'overlay' ? 'active' : ''}`}
            onClick={() => setMode('overlay')}
          >
            Overlay
          </button>
        </div>
        <div className="preview-zoom">
          <button className="icon-btn" onClick={zoomOut} aria-label="Zoom out">
            −
          </button>
          <span className="preview-zoom-level">{Math.round(scale * 100)}%</span>
          <button className="icon-btn" onClick={zoomIn} aria-label="Zoom in">
            +
          </button>
          <button className="icon-btn" onClick={zoomFit} aria-label="Fit to window">
            ☐
          </button>
        </div>
        {onDownload && resultSrc && (
          <button className="btn btn-sm btn-primary" onClick={onDownload}>
            Download
          </button>
        )}
      </div>

      <div className="preview-body" ref={containerRef}>
        {!hasContent && (
          <div className="preview-placeholder">
            <div className="preview-placeholder-icon">🖼</div>
            <div>Select a task to preview</div>
          </div>
        )}

        {hasContent && mode === 'side-by-side' && (
          <div className="preview-side-by-side" style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}>
            <div className="preview-panel">
              <div className="preview-panel-label">Original</div>
              {originalSrc ? (
                <img className="preview-image" src={originalSrc} alt="Original" draggable={false} />
              ) : (
                <div className="preview-panel-empty">No original</div>
              )}
            </div>
            <div className="preview-panel">
              <div className="preview-panel-label">Result</div>
              {resultSrc ? (
                <img className="preview-image" src={resultSrc} alt="Result" draggable={false} />
              ) : (
                <div className="preview-panel-empty">No result</div>
              )}
            </div>
          </div>
        )}

        {hasContent && mode === 'overlay' && (
          <div
            className="preview-overlay"
            onMouseMove={handleOverlayMouseMove}
            onMouseUp={handleOverlayMouseUp}
            onMouseLeave={handleOverlayMouseUp}
            style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}
          >
            <div className="preview-overlay-base">
              {originalSrc ? (
                <img className="preview-image" src={originalSrc} alt="Original" draggable={false} />
              ) : (
                <div className="preview-panel-empty">No original</div>
              )}
            </div>
            <div
              className="preview-overlay-top"
              style={{ clipPath: `inset(0 ${100 - overlayPos}% 0 0)` }}
            >
              {resultSrc ? (
                <img className="preview-image" src={resultSrc} alt="Result" draggable={false} />
              ) : (
                <div className="preview-panel-empty">No result</div>
              )}
            </div>
            <div
              className="preview-overlay-slider"
              style={{ left: `${overlayPos}%` }}
              onMouseDown={handleOverlayMouseDown}
            >
              <div className="preview-overlay-handle">↔</div>
            </div>
          </div>
        )}
      </div>

      {fileName && <div className="preview-footer">{fileName}</div>}
    </div>
  );
};
