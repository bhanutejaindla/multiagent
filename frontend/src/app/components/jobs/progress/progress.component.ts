import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService, Job } from '../../../services/api.service';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-progress',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './progress.component.html',
  styleUrls: ['./progress.component.css']
})
export class ProgressComponent implements OnInit, OnDestroy {
  jobId!: number;
  job: Job | null = null;
  loading: boolean = true;
  error: string = '';
  private subscription?: Subscription;
  private pollInterval = 2000; // Poll every 2 seconds

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService
  ) { }

  ngOnInit() {
    this.jobId = +this.route.snapshot.paramMap.get('id')!;
    this.loadJob();
    this.startPolling();
  }

  ngOnDestroy() {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }

  loadJob() {
    this.apiService.getJob(this.jobId).subscribe({
      next: (job) => {
        this.job = job;
        this.loading = false;

        // Redirect to report view if completed
        if (job.status === 'completed') {
          setTimeout(() => {
            const reportId = job.reports && job.reports.length > 0 ? job.reports[0].id : job.id;
            this.router.navigate(['/reports', reportId]);
          }, 2000);
        }
      },
      error: (err) => {
        this.error = 'Failed to load job progress';
        this.loading = false;
      }
    });
  }

  currentAgent: string = 'Initializing...';
  estimatedTimeRemaining: string = 'Calculating...';
  simulatedProgress: number = 0;

  startPolling() {
    // Simulate progress for better UX
    const startTime = Date.now();
    const estimatedDuration = 240000; // 4 minutes in ms

    this.subscription = interval(this.pollInterval)
      .pipe(
        switchMap(() => this.apiService.getJob(this.jobId))
      )
      .subscribe({
        next: (job) => {
          this.job = job;

          // Update simulated progress based on time if job is running
          if (job.status === 'running') {
            const elapsed = Date.now() - startTime;
            const timeProgress = Math.min((elapsed / estimatedDuration) * 100, 95);
            this.simulatedProgress = Math.max(this.simulatedProgress, timeProgress, job.progress);

            // Calculate remaining time
            const remainingMs = Math.max(0, estimatedDuration - elapsed);
            const minutes = Math.floor(remainingMs / 60000);
            const seconds = Math.floor((remainingMs % 60000) / 1000);
            this.estimatedTimeRemaining = `${minutes}m ${seconds}s`;

            // Cycle agent names based on progress
            if (this.simulatedProgress < 20) this.currentAgent = 'Ingestion Agent: Analyzing documents...';
            else if (this.simulatedProgress < 40) this.currentAgent = 'Web Research Agent: Searching online sources...';
            else if (this.simulatedProgress < 60) this.currentAgent = 'Synthesis Agent: Structuring report...';
            else if (this.simulatedProgress < 80) this.currentAgent = 'Citation Agent: Verifying sources...';
            else this.currentAgent = 'Compliance Agent: Finalizing report...';

          } else if (job.status === 'completed') {
            this.simulatedProgress = 100;
            this.currentAgent = 'All tasks completed!';
            this.estimatedTimeRemaining = '0m 0s';
            if (this.subscription) {
              this.subscription.unsubscribe();
            }
          } else if (job.status === 'failed') {
            this.currentAgent = 'Job Failed';
            if (this.subscription) {
              this.subscription.unsubscribe();
            }
          }
        },
        error: (err) => {
          console.error('Error polling job:', err);
        }
      });
  }

  cancelJob() {
    if (confirm('Are you sure you want to cancel this job?')) {
      this.apiService.cancelJob(this.jobId).subscribe({
        next: () => {
          this.router.navigate(['/dashboard']);
        },
        error: (err) => {
          this.error = 'Failed to cancel job';
        }
      });
    }
  }

  getTaskStatus(task: any): string {
    if (!task) return 'pending';
    return task.status || 'pending';
  }

  getTaskProgress(task: any): number {
    if (!task) return 0;
    return task.progress || 0;
  }
}

