import React, { useState, useCallback, useRef } from 'react';
import { useInvoke } from '../hooks/useInvoke';

interface PreviewPaneProps {
  originalSrc?: string;
  resultSrc?: string;
  fileName?: string;
  inputPath?: string;
  options?: string;
  outputFormat?: 'svg' | 'pdf' | 'png';
  onDownload?: () => void;
  onToast?: (message: string, type?: 'success' | 'error') => void;
  // v1.2 cloud share
  onCloudShare?: () => void;
  shareUrl?: string;
  shareQrCode?: string;
  // v2.0 animation
  onGenerateAnimation?: () => void;
  animationPreset?: string;
  onChangeAnimationPreset?: (preset: string) => void;
  animationFormat?: string;
  onChangeAnimationFormat?: (format: string) => void;
  animationResultPath?: string;
  // v2.0 collaboration
  collabRoomId?: string | null;
  collabUsers?: string[];
}

export const PreviewPane: React.FC<PreviewPaneProps> = ({
  originalSrc,
  resultSrc,
  fileName,
  inputPath,
  options,
  outputFormat = 'svg',
  onDownload,
  onToast,
  onCloudShare,
  shareUrl,
  shareQrCode,
  onGenerateAnimation,
  animationPreset = '绘制',
  onChangeAnimationPreset,
  animationFormat = 'SMIL',
  onChangeAnimationFormat,
  animationResultPath,
  collabRoomId,
  collabUsers = [],
}) => {
  const [mode, setMode] = useState<'side-by-side' | 'overlay'>('side-by-side');
  const [overlayPos, setOverlayPos] = useState(50);
  const [scale, setScale] = useState(1);
  const [localResult, setLocalResult] = useState<string | undefined>(resultSrc);
  const [converting, setConverting] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const { call: callConvert } = useInvoke<{ inputPath: string; options: string }, string>('convert_image');
  const { call: callOpenEditor } = useInvoke<{ svgPath: string; editor?: string }, void>('open_with_editor');

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

  const handleConvert = useCallback(async () => {
    if (!inputPath || !options) {
      onToast?.('No input image or options set', 'error');
      return;
    }
    setConverting(true);
    const result = await callConvert({ inputPath, options });
    setConverting(false);
    if (result) {
      try {
        const parsed = JSON.parse(result) as { outputPath?: string };
        if (parsed.outputPath) {
          setLocalResult(parsed.outputPath);
          onToast?.('Conversion complete', 'success');
        } else {
          onToast?.('Conversion returned no output path', 'error');
        }
      } catch {
        onToast?.('Failed to parse conversion result', 'error');
      }
    } else {
      onToast?.('Conversion failed', 'error');
    }
  }, [inputPath, options, callConvert, onToast]);

  const handleOpenEditor = useCallback(async () => {
    const svgPath = localResult || resultSrc;
    if (!svgPath) {
      onToast?.('No result to open', 'error');
      return;
    }
    const result = await callOpenEditor({ svgPath });
    if (result !== null) {
      onToast?.('Opened in external editor', 'success');
    } else {
      onToast?.('Failed to open external editor', 'error');
    }
  }, [localResult, resultSrc, callOpenEditor, onToast]);

  const handleDownload = useCallback(() => {
    onDownload?.();
  }, [onDownload]);

  const displayResult = localResult || resultSrc;
  const hasContent = originalSrc || displayResult;

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
        <div className="preview-actions">
          {inputPath && (
            <button className="btn btn-sm btn-primary" onClick={handleConvert} disabled={converting}>
              {converting ? 'Converting...' : 'Convert'}
            </button>
          )}
          {displayResult && (
            <button className="btn btn-sm" onClick={handleOpenEditor}>
              Open Editor
            </button>
          )}
          {displayResult && (
            <button className="btn btn-sm btn-secondary" onClick={handleDownload}>
              Download {outputFormat.toUpperCase()}
            </button>
          )}
          {displayResult && (
            <button className="btn btn-sm btn-secondary" onClick={onCloudShare}>
              ☁️ Share
            </button>
          )}
          {displayResult && (
            <button className="btn btn-sm btn-secondary" onClick={onGenerateAnimation}>
              🎬 Animate
            </button>
          )}
        </div>
      </div>

      {shareUrl && (
        <div className="preview-share-bar" style={{ padding: '8px 12px', background: '#f5f5f5', borderBottom: '1px solid #ddd', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 14 }}>☁️ Share URL:</span>
          <a href={shareUrl} target="_blank" rel="noreferrer" style={{ fontSize: 14, color: '#0066cc' }}>{shareUrl}</a>
          {shareQrCode && (
            <img src={shareQrCode} alt="QR" style={{ width: 48, height: 48, marginLeft: 'auto' }} />
          )}
        </div>
      )}

      {/* v2.0: Collaboration status */}
      {collabRoomId && (
        <div className="preview-collab-bar" style={{ padding: '6px 12px', background: 'rgba(10,132,255,0.08)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, fontSize: 12 }}>
          <span>👥 Room: <strong>{collabRoomId}</strong></span>
          <span>Users: {collabUsers.length > 0 ? collabUsers.join(', ') : 'Just you'}</span>
        </div>
      )}

      {/* v2.0: Animation controls */}
      {displayResult && (
        <div className="preview-anim-bar" style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, fontSize: 12 }}>
          <span>🎬 Animation:</span>
          <select
            value={animationPreset}
            onChange={(e) => onChangeAnimationPreset?.(e.target.value)}
            style={{ fontSize: 12, padding: '2px 6px' }}
          >
            <option value="绘制">Draw</option>
            <option value="揭示">Reveal</option>
            <option value="变形">Morph</option>
            <option value="脉冲">Pulse</option>
            <option value="颜色循环">Color Loop</option>
          </select>
          <select
            value={animationFormat}
            onChange={(e) => onChangeAnimationFormat?.(e.target.value)}
            style={{ fontSize: 12, padding: '2px 6px' }}
          >
            <option value="SMIL">SMIL</option>
            <option value="Lottie">Lottie</option>
            <option value="GIF">GIF</option>
            <option value="CSS">CSS</option>
          </select>
          {animationResultPath && (
            <span style={{ color: 'var(--success)' }}>✓ {animationResultPath}</span>
          )}
        </div>
      )}

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
              {displayResult ? (
                <img className="preview-image" src={displayResult} alt="Result" draggable={false} />
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
              {displayResult ? (
                <img className="preview-image" src={displayResult} alt="Result" draggable={false} />
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
