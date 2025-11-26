import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService, SystemStats, User, ToolStatus } from '../../services/admin.service';

@Component({
    selector: 'app-admin',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './admin.component.html',
    styleUrls: ['./admin.component.css']
})
export class AdminComponent implements OnInit {
    private adminService = inject(AdminService);

    stats: SystemStats | null = null;
    users: User[] = [];
    tools: ToolStatus[] = [];
    loading = true;
    error = '';

    ngOnInit() {
        this.loadData();
    }

    loadData() {
        this.loading = true;
        this.adminService.getStats().subscribe({
            next: (data) => {
                this.stats = data;
                this.loadUsers();
            },
            error: (err) => {
                this.error = 'Failed to load admin data';
                this.loading = false;
                console.error(err);
            }
        });
    }

    loadUsers() {
        this.adminService.getUsers().subscribe({
            next: (data) => {
                this.users = data;
                this.loadTools();
            },
            error: (err) => console.error(err)
        });
    }

    loadTools() {
        this.adminService.getTools().subscribe({
            next: (data) => {
                this.tools = data;
                this.loading = false;
            },
            error: (err) => {
                this.loading = false;
                console.error(err);
            }
        });
    }

    updateQuota(user: User, newQuota: string) {
        const quota = parseInt(newQuota, 10);
        if (isNaN(quota) || quota < 0) return;

        this.adminService.updateQuota(user.id, quota).subscribe({
            next: () => {
                user.quota_limit = quota;
                alert(`Quota updated for ${user.username}`);
            },
            error: (err) => {
                console.error(err);
                alert('Failed to update quota');
            }
        });
    }

    toggleTool(tool: ToolStatus) {
        const newState = !tool.is_enabled;
        this.adminService.toggleTool(tool.name, newState).subscribe({
            next: () => {
                tool.is_enabled = newState;
                tool.status = newState ? 'available' : 'disabled';
            },
            error: (err) => {
                console.error(err);
                // Revert UI on error
                tool.is_enabled = !newState;
                alert('Failed to toggle tool');
            }
        });
    }
}
