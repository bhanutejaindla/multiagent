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
  ) {}

  ngOnInit() {
    this.reportId = +this.route.snapshot.paramMap.get('id')!;
    this.loadReport();
  }

  loadReport() {
    this.apiService.getReport(this.reportId).subscribe({
      next: (report) => {
        this.report = report;
        this.editedContent = report.content;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load report';
        this.loading = false;
      }
    });
  }

  saveReport() {
    if (!this.editedContent.trim()) {
      this.error = 'Report content cannot be empty';
      return;
    }

    this.saving = true;
    this.error = '';

    this.apiService.updateReport(this.reportId, this.editedContent).subscribe({
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

