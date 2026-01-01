import { useState, useCallback } from 'react';
import { Upload, File, CheckCircle, XCircle } from 'lucide-react';
import { importOreadFile, importFhirBundle, importCCDA } from '../lib/api';

interface ImportResult {
  success: boolean;
  import_id?: string;
  patient_count: number;
  details?: any;
  errors: string[];
}

export default function Import() {
  const [isDragging, setIsDragging] = useState(false);
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState<ImportResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  async function handleFiles(files: FileList) {
    setImporting(true);
    setError(null);
    const newResults: ImportResult[] = [];

    for (const file of Array.from(files)) {
      const isJson = file.name.endsWith('.json');
      const isXml = file.name.endsWith('.xml');

      if (!isJson && !isXml) {
        newResults.push({
          success: false,
          patient_count: 0,
          errors: [`${file.name}: Must be a JSON or XML file`],
        });
        continue;
      }

      try {
        const text = await file.text();

        if (isXml) {
          // C-CDA XML file
          const newFile = new window.File([text], file.name, { type: 'application/xml' });
          const result = await importCCDA(newFile);

          newResults.push({
            ...result,
            details: {
              ...result.details,
              filename: file.name,
              format: 'C-CDA 2.1',
            },
          });
        } else {
          // JSON file - detect if FHIR Bundle or Oread
          const json = JSON.parse(text);
          const isFhirBundle = json.resourceType === 'Bundle';

          // Create a new file from the text (since we already read it)
          const newFile = new window.File([text], file.name, { type: 'application/json' });

          // Route to appropriate importer
          const result = isFhirBundle
            ? await importFhirBundle(newFile)
            : await importOreadFile(newFile);

          newResults.push({
            ...result,
            details: {
              ...result.details,
              filename: file.name,
              format: isFhirBundle ? 'FHIR R5' : 'Oread JSON',
            },
          });
        }
      } catch (err) {
        newResults.push({
          success: false,
          patient_count: 0,
          errors: [err instanceof Error ? err.message : 'Import failed'],
          details: { filename: file.name },
        });
      }
    }

    setResults(prev => [...newResults, ...prev]);
    setImporting(false);
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
          Import Patients
        </h1>
        <p style={{ color: 'var(--text-secondary)' }} className="mt-1">
          Import patient data from Oread JSON, FHIR R5, or C-CDA files
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className="rounded-xl p-16 text-center transition-all"
        style={{
          border: `2px dashed ${isDragging ? 'var(--accent)' : 'var(--border)'}`,
          backgroundColor: isDragging ? 'var(--accent-light)' : 'var(--bg-card)',
        }}
      >
        <Upload
          className="w-12 h-12 mx-auto mb-4"
          style={{ color: isDragging ? 'var(--accent)' : 'var(--text-tertiary)' }}
        />
        <p className="text-lg font-display font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
          {isDragging ? 'Drop files here' : 'Drag & drop patient files'}
        </p>
        <p style={{ color: 'var(--text-tertiary)' }} className="mb-6">or</p>
        <label className="inline-block">
          <input
            type="file"
            accept=".json,.xml"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <span className="btn-primary cursor-pointer">
            Browse Files
          </span>
        </label>
      </div>

      {/* Importing indicator */}
      {importing && (
        <div
          className="mt-6 p-4 rounded-lg flex items-center gap-3"
          style={{
            backgroundColor: 'var(--accent-light)',
            border: '1px solid rgba(45, 90, 74, 0.2)',
          }}
        >
          <div
            className="w-5 h-5 border-2 rounded-full animate-spin"
            style={{
              borderColor: 'var(--accent-tertiary)',
              borderTopColor: 'var(--accent)',
            }}
          />
          <span style={{ color: 'var(--accent)' }}>Importing files...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          className="mt-6 p-4 rounded-lg"
          style={{
            backgroundColor: 'rgba(155, 44, 44, 0.1)',
            border: '1px solid rgba(155, 44, 44, 0.2)',
            color: 'var(--clinical-error)',
          }}
        >
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-display font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Import Results
          </h2>
          <div className="space-y-3">
            {results.map((result, i) => (
              <div
                key={i}
                className="p-4 rounded-lg"
                style={{
                  backgroundColor: result.success ? 'rgba(45, 106, 79, 0.05)' : 'rgba(155, 44, 44, 0.05)',
                  border: `1px solid ${result.success ? 'rgba(45, 106, 79, 0.2)' : 'rgba(155, 44, 44, 0.2)'}`,
                }}
              >
                <div className="flex items-start gap-3">
                  {result.success ? (
                    <CheckCircle className="w-5 h-5 mt-0.5" style={{ color: 'var(--clinical-success)' }} />
                  ) : (
                    <XCircle className="w-5 h-5 mt-0.5" style={{ color: 'var(--clinical-error)' }} />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <File className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {result.details?.filename || 'Unknown file'}
                      </span>
                    </div>
                    {result.success ? (
                      <div className="mt-1 text-sm" style={{ color: 'var(--clinical-success)' }}>
                        Successfully imported patient
                        {result.details?.counts && (
                          <span style={{ opacity: 0.8 }} className="ml-2">
                            ({Object.entries(result.details.counts).map(([k, v]) => `${v} ${k}`).join(', ')})
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="mt-1 text-sm" style={{ color: 'var(--clinical-error)' }}>
                        {result.errors.map((err, j) => (
                          <div key={j}>{err}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supported formats */}
      <div className="mt-10 p-6 rounded-xl" style={{ backgroundColor: 'var(--bg-secondary)' }}>
        <h3 className="font-display font-medium mb-3" style={{ color: 'var(--text-primary)' }}>
          Supported Formats
        </h3>
        <ul className="text-sm space-y-2" style={{ color: 'var(--text-secondary)' }}>
          <li className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4" style={{ color: 'var(--clinical-success)' }} />
            Oread JSON patient files (.json)
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4" style={{ color: 'var(--clinical-success)' }} />
            FHIR R5 Bundle (.json)
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4" style={{ color: 'var(--clinical-success)' }} />
            C-CDA 2.1 documents (.xml)
          </li>
        </ul>
      </div>
    </div>
  );
}
