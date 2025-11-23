import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Report } from '../../../services/api.service';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

@Component({
  selector: 'app-report-view',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './report-view.component.html',
  styleUrls: ['./report-view.component.css']
})
export class ReportViewComponent implements OnInit {
  reportId!: number;
  report: Report | null = null;
  loading: boolean = true;
  error: string = '';

  // Chat
  messages: Message[] = [];
  chatInput: string = '';
  chatLoading: boolean = false;
  showChat: boolean = false;

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
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load report';
        this.loading = false;
      }
    });
  }

  toggleChat() {
    this.showChat = !this.showChat;
  }

  sendChatMessage() {
    if (!this.chatInput.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: this.chatInput,
      timestamp: new Date()
    };
    this.messages.push(userMessage);
    this.chatInput = '';
    this.chatLoading = true;

    this.apiService.sendChatMessage(userMessage.content, this.reportId).subscribe({
      next: (response) => {
        const assistantMessage: Message = {
          role: 'assistant',
          content: response.response,
          timestamp: new Date()
        };
        this.messages.push(assistantMessage);
        this.chatLoading = false;
      },
      error: (err) => {
        const errorMessage: Message = {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date()
        };
        this.messages.push(errorMessage);
        this.chatLoading = false;
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

  editReport() {
    this.router.navigate(['/reports', this.reportId, 'edit']);
  }

  parseContent(content: string): string {
    // Simple markdown-like parsing for citations
    return content
      .replace(/\[citation:(\d+)\]/g, '<span class="citation">[Citation $1]</span>')
      .replace(/\n/g, '<br>');
  }
}

