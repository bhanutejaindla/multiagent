import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Job {
    id: number;
    name: string;
    type: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
    progress: number;
    tasks?: any[];
}

@Injectable({
    providedIn: 'root'
})
export class JobService {
    private http = inject(HttpClient);
    private apiUrl = `${environment.apiBaseUrl}/jobs`;

    getJobs(page: number = 1, limit: number = 10): Observable<Job[]> {
        const skip = (page - 1) * limit;
        let params = new HttpParams()
            .set('skip', skip.toString())
            .set('limit', limit.toString());

        return this.http.get<Job[]>(this.apiUrl, { params });
    }

    getJob(id: number): Observable<Job> {
        return this.http.get<Job>(`${this.apiUrl}/${id}`);
    }

    createJob(jobData: any): Observable<any> {
        return this.http.post<any>(this.apiUrl, jobData);
    }

    // Placeholder for cancel functionality
    cancelJob(id: number): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/${id}/cancel`, {});
    }
}
