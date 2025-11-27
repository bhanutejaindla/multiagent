import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Report } from '../../../services/api.service';

@Component({
  selector: 'app-report-edit',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './report-edit.component.html',
  styleUrls: ['./report-edit.component.css']
})
export class ReportEditComponent implements OnInit {
  reportId!: number;
  report: Report | null = null;
  editedContent: string = '';
  loading: boolean = true;
  saving: boolean = false;
  error: string = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService
  ) { }

  ngOnInit() {
    this.reportId = +this.route.snapshot.paramMap.get('id')!;
    this.loadReport();
  }

  // Form fields
  executiveSummary: string = '';
  findings: string = '';
  risks: string = '';
  fullText: string = '';
  isStructured: boolean = false;

  loadReport() {
    this.apiService.getReport(this.reportId).subscribe({
      next: (report) => {
        this.report = report;

        if (report.content && typeof report.content === 'object') {
          this.isStructured = true;
          this.executiveSummary = report.content.executive_summary || '';
          this.findings = Array.isArray(report.content.findings) ? report.content.findings.join('\n') : '';
          this.risks = Array.isArray(report.content.risks) ? report.content.risks.join('\n') : '';
          this.fullText = report.content.full_text || '';
        } else {
          this.isStructured = false;
          this.editedContent = typeof report.content === 'string' ? report.content : JSON.stringify(report.content, null, 2);
        }

        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load report';
        this.loading = false;
      }
    });
  }

  saveReport() {
    let contentToSave: any;

    if (this.isStructured) {
      contentToSave = {
        ...this.report?.content, // Keep existing fields like citations
        executive_summary: this.executiveSummary,
        findings: this.findings.split('\n').filter(line => line.trim()),
        risks: this.risks.split('\n').filter(line => line.trim()),
        full_text: this.fullText
      };
    } else {
      if (!this.editedContent.trim()) {
        this.error = 'Report content cannot be empty';
        return;
      }
      contentToSave = this.editedContent;
    }

    this.saving = true;
    this.error = '';

    const jobId = this.report?.job_id || this.reportId;
    this.apiService.updateReport(jobId, contentToSave).subscribe({
      next: (updatedReport) => {
        this.saving = false;
        this.router.navigate(['/reports', this.reportId]);
      },
      error: (err) => {
        this.error = err.error?.detail || 'Failed to save report';
        this.saving = false;
      }
    });
  }

  downloadReport(format: 'pdf' | 'docx') {
    this.apiService.downloadReport(this.reportId, format).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report_${this.reportId}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      },
      error: (err) => {
        alert('Failed to download report');
      }
    });
  }

  cancel() {
    if (confirm('Are you sure you want to discard your changes?')) {
      this.router.navigate(['/reports', this.reportId]);
    }
  }
}

