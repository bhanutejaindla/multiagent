import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../services/api.service';
import { AuthService } from '../../../services/auth.service';

interface Tool {
  id: string;
  name: string;
  enabled: boolean;
  quota: number;
  usage: number;
  description: string;
}

interface Metrics {
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  activeJobs: number;
  errorRate: number;
  averageJobTime: number;
}

@Component({
  selector: 'app-admin-panel',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './admin-panel.component.html',
  styleUrls: ['./admin-panel.component.css']
})
export class AdminPanelComponent implements OnInit {
  tools: Tool[] = [];
  metrics: Metrics | null = null;
  loading: boolean = true;
  error: string = '';

  constructor(
    private apiService: ApiService,
    private authService: AuthService
  ) {}

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.loading = true;
    
    // Load tools and metrics in parallel
    this.apiService.getToolRegistry().subscribe({
      next: (tools) => {
        this.tools = tools;
        this.checkLoadingComplete();
      },
      error: (err) => {
        console.error('Error loading tools:', err);
        // Use mock data if API fails
        this.tools = this.getMockTools();
        this.checkLoadingComplete();
      }
    });

    this.apiService.getAdminMetrics().subscribe({
      next: (metrics) => {
        this.metrics = metrics;
        this.checkLoadingComplete();
      },
      error: (err) => {
        console.error('Error loading metrics:', err);
        // Use mock data if API fails
        this.metrics = this.getMockMetrics();
        this.checkLoadingComplete();
      }
    });
  }

  checkLoadingComplete() {
    if (this.tools.length > 0 && this.metrics) {
      this.loading = false;
    }
  }

  updateToolQuota(tool: Tool) {
    this.apiService.updateToolQuota(tool.id, tool.quota).subscribe({
      next: () => {
        alert(`Quota updated for ${tool.name}`);
      },
      error: (err) => {
        alert(`Failed to update quota: ${err.error?.detail || 'Unknown error'}`);
      }
    });
  }

  toggleTool(tool: Tool) {
    tool.enabled = !tool.enabled;
    // TODO: Implement API call to enable/disable tool
    console.log(`Tool ${tool.id} ${tool.enabled ? 'enabled' : 'disabled'}`);
  }

  getQuotaPercentage(tool: Tool): number {
    if (tool.quota === 0) return 0;
    return Math.min((tool.usage / tool.quota) * 100, 100);
  }

  getQuotaColor(tool: Tool): string {
    const percentage = this.getQuotaPercentage(tool);
    if (percentage >= 90) return '#e74c3c';
    if (percentage >= 70) return '#f39c12';
    return '#27ae60';
  }

  private getMockTools(): Tool[] {
    return [
      {
        id: 'web_search',
        name: 'Web Search',
        enabled: true,
        quota: 100,
        usage: 45,
        description: 'Search the web for relevant information'
      },
      {
        id: 'rag',
        name: 'RAG',
        enabled: true,
        quota: 200,
        usage: 120,
        description: 'Retrieval Augmented Generation from knowledge base'
      },
      {
        id: 'compliance',
        name: 'Compliance Check',
        enabled: true,
        quota: 50,
        usage: 30,
        description: 'PII redaction and compliance verification'
      },
      {
        id: 'citation_validation',
        name: 'Citation Validation',
        enabled: true,
        quota: 100,
        usage: 75,
        description: 'Verify and validate citations in reports'
      }
    ];
  }

  private getMockMetrics(): Metrics {
    return {
      totalJobs: 150,
      completedJobs: 120,
      failedJobs: 10,
      activeJobs: 20,
      errorRate: 6.67,
      averageJobTime: 45.5
    };
  }
}

