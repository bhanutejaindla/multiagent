import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface Job {
  id: number;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  user_id: number;
  progress: number;
  tasks?: any[];
  created_at: string;
  started_at?: string;
  updated_at: string;
}

export interface Report {
  id: number;
  job_id: number;
  content: string;
  citations?: any[];
  created_at: string;
}

export interface CreateJobRequest {
  topic: string;
  documents?: File[];
  tool_config?: {
    [key: string]: boolean;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  private getHeaders(): HttpHeaders {
    const authHeaders = this.authService.getAuthHeaders();
    return new HttpHeaders({
      ...authHeaders,
      'Content-Type': 'application/json'
    });
  }

  private getFormHeaders(): HttpHeaders {
    const authHeaders = this.authService.getAuthHeaders();
    return new HttpHeaders(authHeaders);
  }

  // Jobs
  createJob(jobData: CreateJobRequest): Observable<{ job_id: number; status: string }> {
    const formData = new FormData();
    formData.append('topic', jobData.topic);
    if (jobData.documents) {
      jobData.documents.forEach(file => {
        formData.append('documents', file);
      });
    }
    if (jobData.tool_config) {
      formData.append('tool_config', JSON.stringify(jobData.tool_config));
    }

    return this.http.post<{ job_id: number; status: string }>(
      `${environment.apiBaseUrl}/jobs`,
      formData,
      { headers: this.getFormHeaders() }
    );
  }

  getJob(jobId: number): Observable<Job> {
    return this.http.get<Job>(
      `${environment.apiBaseUrl}/jobs/${jobId}`,
      { headers: this.getHeaders() }
    );
  }

  getJobs(params?: { page?: number; limit?: number; status?: string }): Observable<{ jobs: Job[]; total: number }> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', params.page);
    if (params?.limit) httpParams = httpParams.set('limit', params.limit);
    if (params?.status) httpParams = httpParams.set('status', params.status);

    return this.http.get<{ jobs: Job[]; total: number }>(
      `${environment.apiBaseUrl}/jobs`,
      { headers: this.getHeaders(), params: httpParams }
    );
  }

  cancelJob(jobId: number): Observable<void> {
    return this.http.post<void>(
      `${environment.apiBaseUrl}/jobs/${jobId}/cancel`,
      {},
      { headers: this.getHeaders() }
    );
  }

  // Reports
  getReport(reportId: number): Observable<Report> {
    return this.http.get<Report>(
      `${environment.apiBaseUrl}/reports/${reportId}`,
      { headers: this.getHeaders() }
    );
  }

  getReports(jobId?: number): Observable<Report[]> {
    let url = `${environment.apiBaseUrl}/reports`;
    if (jobId) {
      url += `?job_id=${jobId}`;
    }
    return this.http.get<Report[]>(url, { headers: this.getHeaders() });
  }

  downloadReport(reportId: number, format: 'pdf' | 'docx'): Observable<Blob> {
    return this.http.get(
      `${environment.apiBaseUrl}/reports/${reportId}/download?format=${format}`,
      { headers: this.getHeaders(), responseType: 'blob' }
    );
  }

  updateReport(reportId: number, content: string): Observable<Report> {
    return this.http.put<Report>(
      `${environment.apiBaseUrl}/reports/${reportId}`,
      { content },
      { headers: this.getHeaders() }
    );
  }

  // Chat
  sendChatMessage(message: string, reportId?: number): Observable<{ response: string }> {
    const body: any = { message };
    if (reportId) {
      body.report_id = reportId;
    }
    return this.http.post<{ response: string }>(
      `${environment.apiBaseUrl}/chat`,
      body,
      { headers: this.getHeaders() }
    );
  }

  // Admin
  getAdminMetrics(): Observable<any> {
    return this.http.get(
      `${environment.apiBaseUrl}/admin/metrics`,
      { headers: this.getHeaders() }
    );
  }

  getToolRegistry(): Observable<any[]> {
    return this.http.get<any[]>(
      `${environment.apiBaseUrl}/admin/tools`,
      { headers: this.getHeaders() }
    );
  }

  updateToolQuota(toolId: string, quota: number): Observable<void> {
    return this.http.put<void>(
      `${environment.apiBaseUrl}/admin/tools/${toolId}/quota`,
      { quota },
      { headers: this.getHeaders() }
    );
  }

  // Document upload
  uploadDocument(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(
      `${environment.apiBaseUrl}/ingest`,
      formData,
      { headers: this.getFormHeaders() }
    );
  }
}

