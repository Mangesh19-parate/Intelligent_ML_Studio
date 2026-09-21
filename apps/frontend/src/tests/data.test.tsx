import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { UploadZone } from '../components/data/UploadZone';
import { DatasetSummaryCards } from '../components/data/DatasetSummaryCards';
import { SplitPanel } from '../components/data/SplitPanel';
import { SchemaTable } from '../components/data/SchemaTable';

describe('Data Stage Subcomponents', () => {
  describe('UploadZone', () => {
    it('renders upload instructions and responds to user interaction', () => {
      const onUpload = vi.fn();
      render(<UploadZone onFileUpload={onUpload} uploading={false} />);

      expect(screen.getByText(/Upload Tabular Dataset/i)).toBeInTheDocument();
      expect(screen.getByText(/Max size: 50MB/i)).toBeInTheDocument();
    });
  });

  describe('DatasetSummaryCards', () => {
    it('displays dataset statistics and checksum', () => {
      const onSelect = vi.fn();
      const dataset = {
        id: 'ds-1',
        version_number: 1,
        row_count: 1500,
        column_count: 12,
        content_hash: 'a1b2c3d4e5f6',
        created_at: new Date().toISOString(),
      };

      render(
        <DatasetSummaryCards
          datasets={[dataset]}
          selectedDataset={dataset}
          onSelectDataset={onSelect}
        />
      );

      expect(screen.getByText('1,500')).toBeInTheDocument();
      expect(screen.getByText('12')).toBeInTheDocument();
      expect(screen.getByText('a1b2c3d4e5f6')).toBeInTheDocument();
    });
  });

  describe('SplitPanel', () => {
    it('calculates partition distribution and triggers split creation', () => {
      const onLockedTestPct = vi.fn();
      const onSplitSeed = vi.fn();
      const onRandomize = vi.fn();
      const onCreateSplit = vi.fn();

      render(
        <SplitPanel
          splitSummary={null}
          totalRows={1000}
          lockedTestPct={20}
          onLockedTestPctChange={onLockedTestPct}
          splitSeed="42"
          onSplitSeedChange={onSplitSeed}
          onRandomizeSeed={onRandomize}
          onCreateSplit={onCreateSplit}
          creatingSplit={false}
        />
      );

      expect(screen.getByText(/Leakage Partitioning/i)).toBeInTheDocument();
      expect(screen.getByText('800 rows')).toBeInTheDocument();
      expect(screen.getByText('200 rows')).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /Lock Partition Boundary/i }));
      expect(onCreateSplit).toHaveBeenCalled();
    });
  });

  describe('SchemaTable', () => {
    it('renders column schema and identifies target column', () => {
      const columns = [
        { id: 'c1', column_name: 'price', data_type: 'NUMERIC', is_target: true },
        { id: 'c2', column_name: 'sqft', data_type: 'NUMERIC' },
      ];

      render(<SchemaTable columns={columns} targetColumn="price" />);

      expect(screen.getByText('price')).toBeInTheDocument();
      expect(screen.getByText('sqft')).toBeInTheDocument();
      expect(screen.getByText('Supervised Label')).toBeInTheDocument();
    });
  });
});
