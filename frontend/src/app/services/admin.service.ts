import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface SystemStats {
    total_jobs: number;
    active_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
    total_users: number;
}

export interface User {
    id: number;
    username: string;
    email: string;
    role: string;
    name: string;
    quota_limit: number;
}

export interface ToolStatus {
    name: string;
    status: string;
    functions: string[];
    is_enabled: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class AdminService {
    private http = inject(HttpClient);
    private apiUrl = `${environment.apiBaseUrl}/admin`;

    getStats(): Observable<SystemStats> {
        return this.http.get<SystemStats>(`${this.apiUrl}/stats`);
    }

    getUsers(): Observable<User[]> {
        return this.http.get<User[]>(`${this.apiUrl}/users`);
    }

    getTools(): Observable<ToolStatus[]> {
        return this.http.get<ToolStatus[]>(`${this.apiUrl}/tools`);
    }

    updateQuota(userId: number, quota: number): Observable<any> {
        return this.http.put(`${this.apiUrl}/users/${userId}/quota`, null, { params: { quota: quota.toString() } });
    }

    toggleTool(toolName: string, enabled: boolean): Observable<any> {
        return this.http.post(`${this.apiUrl}/tools/${toolName}/toggle`, null, { params: { enabled: enabled.toString() } });
    }
}
