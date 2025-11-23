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
  ) {}

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
            this.router.navigate(['/reports', job.id]);
          }, 2000);
        }
      },
      error: (err) => {
        this.error = 'Failed to load job progress';
        this.loading = false;
      }
    });
  }

  startPolling() {
    this.subscription = interval(this.pollInterval)
      .pipe(
        switchMap(() => this.apiService.getJob(this.jobId))
      )
      .subscribe({
        next: (job) => {
          this.job = job;
          if (job.status === 'completed' || job.status === 'failed') {
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

