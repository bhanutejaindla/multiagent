import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ApiService, CreateJobRequest } from '../../../services/api.service';

@Component({
  selector: 'app-create-job',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './create-job.component.html',
  styleUrls: ['./create-job.component.css']
})
export class CreateJobComponent {
  topic: string = '';
  documents: File[] = [];
  toolConfig: {
    web_search: boolean;
    rag: boolean;
    compliance: boolean;
    citation_validation: boolean;
    [key: string]: boolean;
  } = {
      web_search: true,
      rag: true,
      compliance: true,
      citation_validation: true
    };

  errors: { [key: string]: string } = {};
  loading: boolean = false;

  constructor(
    private apiService: ApiService,
    private router: Router
  ) { }

  onFileSelected(event: any) {
    const files = Array.from(event.target.files) as File[];
    this.documents = [...this.documents, ...files];
    this.errors['documents'] = '';
  }

  removeDocument(index: number) {
    this.documents.splice(index, 1);
  }

  validate(): boolean {
    this.errors = {};

    if (!this.topic || this.topic.trim().length < 3) {
      this.errors['topic'] = 'Topic must be at least 3 characters';
      return false;
    }

    if (this.documents.length > 0) {
      const invalidFiles = this.documents.filter(
        file => !file.name.match(/\.(pdf|docx|txt)$/i)
      );
      if (invalidFiles.length > 0) {
        this.errors['documents'] = 'Only PDF, DOCX, and TXT files are allowed';
        return false;
      }
    }

    const hasToolEnabled = Object.values(this.toolConfig).some(enabled => enabled);
    if (!hasToolEnabled) {
      this.errors['tools'] = 'At least one tool must be enabled';
      return false;
    }

    return true;
  }

  onSubmit() {
    if (!this.validate()) {
      return;
    }

    this.loading = true;

    const jobData: CreateJobRequest = {
      topic: this.topic.trim(),
      documents: this.documents.length > 0 ? this.documents : undefined,
      tool_config: this.toolConfig
    };

    this.apiService.createJob(jobData).subscribe({
      next: (response) => {
        this.router.navigate(['/jobs', response.job_id, 'progress']);
      },
      error: (err) => {
        this.errors['submit'] = err.error?.detail || 'Failed to create job. Please try again.';
        this.loading = false;
      }
    });
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }
}

