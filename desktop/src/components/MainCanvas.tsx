import React, { useState, useCallback, useRef, useEffect } from 'react';

interface MainCanvasProps {
  originalImage: string | null;
  resultSvg: string | undefined;
  onDropFiles?: (files: string[]) => void;
  onClickUpload?: () => void;
  fileName?: string;
}

type ViewMode = 'side-by-side' | 'overlay';

const MainCanvas = React.memo<MainCanvasProps>(({
  originalImage,
  resultSvg,
  onDropFiles,
  onClickUpload,
  fileName,
}) => {
  const [mode, setMode] = useState<ViewMode>('side-by-side');
  const [scale, setScale] = useState(1);
  const [overlayPos, setOverlayPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingSlider = useRef(false);

  const hasImage = !!originalImage || !!resultSvg;

  const zoomIn = useCallback(() => setScale((s) => Math.min(s + 0.25, 5)), []);
  const zoomOut = useCallback(() => setScale((s) => Math.max(s - 0.25, 0.25)), []);
  const zoomReset = useCallback(() => setScale(1), []);

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (!hasImage) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setScale((s) => Math.max(0.25, Math.min(5, s + delta)));
    },
    [hasImage]
  );

  const handleDoubleClick = useCallback(() => {
    zoomReset();
  }, [zoomReset]);

  const handleOverlayMouseDown = useCallback(() => {
    isDraggingSlider.current = true;
  }, []);

  const handleOverlayMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDraggingSlider.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setOverlayPos(pct);
    },
    []
  );

  const handleOverlayMouseUp = useCallback(() => {
    isDraggingSlider.current = false;
  }, []);

  useEffect(() => {
    const onUp = () => {
      isDraggingSlider.current = false;
      setIsDragging(false);
    };
    window.addEventListener('mouseup', onUp);
    return () => window.removeEventListener('mouseup', onUp);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const files: string[] = [];
      if (e.dataTransfer.files) {
        for (let i = 0; i < e.dataTransfer.files.length; i++) {
          const f = e.dataTransfer.files[i] as File & { path?: string };
          if (f.path) {
            files.push(f.path);
          }
        }
      }
      if (files.length > 0) {
        onDropFiles?.(files);
      }
    },
    [onDropFiles]
  );

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        background: '#faf9f7',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
      onWheel={handleWheel}
      onDoubleClick={handleDoubleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Toolbar */}
      {hasImage && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 16px',
            borderBottom: '1px solid #e5e3df',
            flexShrink: 0,
            background: '#faf9f7',
          }}
        >
          <div style={{ display: 'flex', gap: 4 }}>
            <ModeButton active={mode === 'side-by-side'} onClick={() => setMode('side-by-side')}>
              并排
            </ModeButton>
            <ModeButton active={mode === 'overlay'} onClick={() => setMode('overlay')}>
              叠加
            </ModeButton>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <IconBtn onClick={zoomOut}>−</IconBtn>
            <span
              style={{
                fontSize: 12,
                fontVariantNumeric: 'tabular-nums',
                minWidth: 44,
                textAlign: 'center',
                color: '#6b6b6b',
              }}
            >
              {Math.round(scale * 100)}%
            </span>
            <IconBtn onClick={zoomIn}>+</IconBtn>
            <IconBtn onClick={zoomReset}>⟲</IconBtn>
          </div>
        </div>
      )}

      {/* Canvas Body */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          overflow: 'auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {!hasImage && (
          <DropZone dragOver={dragOver} onClick={onClickUpload} />
        )}

        {hasImage && mode === 'side-by-side' && (
          <div
            style={{
              display: 'flex',
              gap: 16,
              padding: 24,
              width: '100%',
              height: '100%',
              alignItems: 'center',
              justifyContent: 'center',
              transform: `scale(${scale})`,
              transformOrigin: 'center center',
            }}
          >
            <ImagePanel label="原图" src={originalImage} />
            <ImagePanel label="矢量结果" src={resultSvg} />
          </div>
        )}

        {hasImage && mode === 'overlay' && (
          <div
            style={{
              position: 'relative',
              width: '80%',
              height: '80%',
              transform: `scale(${scale})`,
              transformOrigin: 'center center',
            }}
            onMouseMove={handleOverlayMouseMove}
            onMouseUp={handleOverlayMouseUp}
            onMouseLeave={handleOverlayMouseUp}
          >
            {/* Base image */}
            <div style={{ position: 'absolute', inset: 0 }}>
              {originalImage ? (
                <img
                  src={originalImage}
                  alt="Original"
                  style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                  draggable={false}
                  loading="lazy"
                />
              ) : (
                <EmptyPanel>无原图</EmptyPanel>
              )}
            </div>
            {/* Top image with clip */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                clipPath: `inset(0 ${100 - overlayPos}% 0 0)`,
              }}
            >
              {resultSvg ? (
                <img
                  src={resultSvg}
                  alt="Result"
                  style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                  draggable={false}
                  loading="lazy"
                />
              ) : (
                <EmptyPanel>无结果</EmptyPanel>
              )}
            </div>
            {/* Slider */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: `${overlayPos}%`,
                width: 2,
                background: '#c45c26',
                transform: 'translateX(-50%)',
                cursor: 'ew-resize',
                zIndex: 3,
              }}
              onMouseDown={handleOverlayMouseDown}
            >
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: '#c45c26',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                }}
              >
                ↔
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      {fileName && (
        <div
          style={{
            padding: '6px 16px',
            fontSize: 12,
            color: '#6b6b6b',
            borderTop: '1px solid #e5e3df',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            flexShrink: 0,
            background: '#faf9f7',
          }}
        >
          {fileName}
        </div>
      )}
    </div>
  );
};

const DropZone: React.FC<{ dragOver: boolean; onClick?: () => void }> = ({ dragOver, onClick }) => (
  <button
    onClick={onClick}
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      padding: '64px 80px',
      borderRadius: 12,
      border: `2px dashed ${dragOver ? '#c45c26' : '#e5e3df'}`,
      background: dragOver ? 'rgba(196, 92, 38, 0.04)' : 'transparent',
      color: '#6b6b6b',
      cursor: 'pointer',
      transition: 'border-color 0.2s ease, background 0.2s ease',
      fontFamily: 'inherit',
    }}
  >
    <span style={{ fontSize: 48, opacity: 0.6 }}>🖼️</span>
    <div style={{ fontSize: 16, fontWeight: 600, color: '#1a1a1a' }}>拖拽图片到此处</div>
    <div style={{ fontSize: 13, color: '#6b6b6b' }}>或 点击上传</div>
  </button>
);

const ImagePanel: React.FC<{ label: string; src: string | null | undefined }> = ({ label, src }) => (
  <div
    style={{
      flex: 1,
      minWidth: 0,
      maxWidth: '50%',
      background: '#ffffff',
      borderRadius: 12,
      border: '1px solid #e5e3df',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}
  >
    <div
      style={{
        padding: '6px 12px',
        fontSize: 11,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        color: '#6b6b6b',
        borderBottom: '1px solid #e5e3df',
        background: '#f5f5f7',
      }}
    >
      {label}
    </div>
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      {src ? (
        <img
          src={src}
          alt={label}
          style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block' }}
          draggable={false}
          loading="lazy"
        />
      ) : (
        <span style={{ color: '#a1a1a6', fontSize: 13 }}>无内容</span>
      )}
    </div>
  </div>
);

const EmptyPanel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#a1a1a6',
      fontSize: 13,
    }}
  >
    {children}
  </div>
);

const ModeButton: React.FC<{ active: boolean; onClick: () => void; children: React.ReactNode }> = ({
  active,
  onClick,
  children,
}) => (
  <button
    onClick={onClick}
    style={{
      padding: '4px 12px',
      borderRadius: 6,
      border: `1px solid ${active ? '#c45c26' : '#e5e3df'}`,
      background: active ? '#c45c26' : '#ffffff',
      color: active ? '#ffffff' : '#6b6b6b',
      fontSize: 12,
      cursor: 'pointer',
      fontFamily: 'inherit',
      transition: 'all 0.2s ease',
    }}
  >
    {children}
  </button>
);

const IconBtn: React.FC<{ onClick: () => void; children: React.ReactNode }> = ({ onClick, children }) => (
  <button
    onClick={onClick}
    style={{
      width: 28,
      height: 28,
      borderRadius: 6,
      border: '1px solid #e5e3df',
      background: '#ffffff',
      color: '#6b6b6b',
      fontSize: 14,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'inherit',
      transition: 'background 0.2s ease',
    }}
    onMouseEnter={(e) => {
      (e.currentTarget as HTMLButtonElement).style.background = '#f5f5f7';
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLButtonElement).style.background = '#ffffff';
    }}
  >
    {children}
  </button>
);

export default MainCanvas;
