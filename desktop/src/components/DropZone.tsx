import React, { useState, useCallback } from 'react';

interface DropZoneProps {
  onDropFiles: (files: string[]) => void;
  visible?: boolean;
}

export const DropZone: React.FC<DropZoneProps> = ({ onDropFiles, visible = true }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isOverlay, setIsOverlay] = useState(false);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragging(true);
      setIsOverlay(true);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.relatedTarget === null || !e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
      setIsOverlay(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      setIsOverlay(false);

      const files: string[] = [];
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        for (let i = 0; i < e.dataTransfer.files.length; i++) {
          const file = e.dataTransfer.files[i];
          if (file.type.startsWith('image/')) {
            // In Tauri, dropped files may include path; fallback to name
            const path = (file as unknown as { path?: string }).path || file.name;
            files.push(path);
          }
        }
      }
      if (files.length > 0) {
        onDropFiles(files);
      }
    },
    [onDropFiles]
  );

  if (!visible) return null;

  return (
    <div
      className={`dropzone-overlay ${isOverlay ? 'active' : ''}`}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className={`dropzone-content ${isDragging ? 'highlight' : ''}`}>
        <div className="dropzone-icon">📁</div>
        <div className="dropzone-text">
          <strong>Drop images here</strong>
        </div>
        <div className="dropzone-hint">Supports PNG, JPG, BMP, TIFF, WebP</div>
      </div>
    </div>
  );
};
