import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { JobService, Job } from '../../services/job.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  private jobService = inject(JobService);
  public authService = inject(AuthService);

  jobs: Job[] = [];
  loading: boolean = true;
  error: string = '';

  // Pagination
  currentPage: number = 1;
  pageSize: number = 10;
  hasMore: boolean = false; // Simple check, ideally backend returns total count

  ngOnInit(): void {
    this.loadJobs();
  }

  loadJobs(): void {
    this.loading = true;
    this.jobService.getJobs(this.currentPage, this.pageSize).subscribe({
      next: (data) => {
        this.jobs = data;
        this.loading = false;
        // Heuristic for pagination if backend doesn't return count
        this.hasMore = data.length === this.pageSize;
      },
      error: (err) => {
        this.error = 'Failed to load jobs.';
        this.loading = false;
        console.error(err);
      }
    });
  }

  nextPage(): void {
    if (this.hasMore) {
      this.currentPage++;
      this.loadJobs();
    }
  }

  prevPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadJobs();
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'failed': return 'status-failed';
      case 'running': return 'status-running';
      default: return 'status-pending';
    }
  }
}
