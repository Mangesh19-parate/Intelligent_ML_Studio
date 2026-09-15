import React, { useRef } from 'react';
import { Upload, FileSpreadsheet, AlertTriangle } from 'lucide-react';
import { Button } from '../ui/Button';

interface UploadZoneProps {
  onFileUpload: (file: File) => void;
  uploading: boolean;
  disabled?: boolean;
}

const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB safeguard

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileUpload,
  uploading,
  disabled = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [uploadError, setUploadError] = React.useState('');

  const handleFile = (file: File) => {
    setUploadError('');
    if (file.size > MAX_SIZE_BYTES) {
      setUploadError(`File exceeds maximum allowed upload size of 50MB (${(file.size / (1024 * 1024)).toFixed(1)}MB).`);
      return;
    }
    if (!file.name.endsWith('.csv')) {
      setUploadError('Only CSV (.csv) files are supported for tabular ML ingestion.');
      return;
    }
    onFileUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled || uploading) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => {
          if (!uploading && !disabled) fileInputRef.current?.click();
        }}
        className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
          dragOver
            ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)]/20'
            : 'border-[var(--color-border)] bg-[var(--color-surface-card)] hover:border-[var(--color-accent)] hover:bg-[var(--color-surface-hover)]'
        } ${uploading || disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFile(e.target.files[0]);
            }
          }}
        />

        <div className="space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-[var(--color-accent-soft)] text-[var(--color-accent)] flex items-center justify-center mx-auto">
            {uploading ? (
              <FileSpreadsheet className="w-6 h-6 animate-pulse" />
            ) : (
              <Upload className="w-6 h-6" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-[var(--color-text)]">
              {uploading ? 'Uploading and streaming tabular dataset...' : 'Upload Tabular Dataset (CSV)'}
            </h3>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              Drag and drop your file here, or click to browse. Max size: 50MB.
            </p>
          </div>
        </div>
      </div>

      {uploadError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}
    </div>
  );
};
