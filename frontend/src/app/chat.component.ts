import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

@Component({
    selector: 'app-chat',
    standalone: true,
    imports: [CommonModule, FormsModule, HttpClientModule],
    template: `
    <div class="chat-container">
      <div class="messages">
        <div *ngFor="let msg of messages" class="message" [ngClass]="msg.role">
          <div class="bubble">{{ msg.content }}</div>
        </div>
        <div *ngIf="loading" class="message assistant">
          <div class="bubble">Thinking...</div>
        </div>
      </div>

      <div class="input-area">
        <div *ngIf="file" class="file-preview">
          {{ file.name }} <button (click)="file = null">x</button>
        </div>
        <div class="controls">
          <input type="file" (change)="onFileSelected($event)" #fileInput style="display:none">
          <button (click)="fileInput.click()" class="icon-btn">📎</button>
          <input [(ngModel)]="input" (keydown.enter)="sendMessage()" placeholder="Ask or upload..." [disabled]="loading">
          <button (click)="sendMessage()" [disabled]="loading || (!input && !file)">Send</button>
        </div>
      </div>
    </div>
  `,
    styles: [`
    .chat-container { display: flex; flex-direction: column; height: 600px; max-width: 800px; margin: 20px auto; border: 1px solid #ccc; border-radius: 8px; overflow: hidden; font-family: sans-serif; }
    .messages { flex: 1; overflow-y: auto; padding: 20px; background: #f9f9f9; }
    .message { display: flex; margin-bottom: 10px; }
    .message.user { justify-content: flex-end; }
    .message.assistant { justify-content: flex-start; }
    .bubble { max-width: 70%; padding: 10px 15px; border-radius: 15px; white-space: pre-wrap; }
    .user .bubble { background: #007bff; color: white; }
    .assistant .bubble { background: white; border: 1px solid #ddd; color: black; }
    .input-area { padding: 15px; background: white; border-top: 1px solid #ddd; }
    .file-preview { background: #eef; padding: 5px; margin-bottom: 5px; border-radius: 4px; font-size: 0.9em; }
    .controls { display: flex; gap: 10px; }
    input[type="text"] { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
    button { padding: 8px 15px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px; }
    button:disabled { background: #ccc; }
    .icon-btn { background: none; color: #555; font-size: 1.2em; padding: 0 10px; }
    .icon-btn:hover { background: #f0f0f0; }
  `]
})
export class ChatComponent {
    messages: Message[] = [];
    input: string = '';
    loading: boolean = false;
    file: File | null = null;

    constructor(private http: HttpClient) { }

    onFileSelected(event: any) {
        this.file = event.target.files[0];
    }

    async sendMessage() {
        if (!this.input.trim() && !this.file) return;

        const userMessage = this.input;
        this.messages.push({ role: 'user', content: userMessage + (this.file ? ` [Attached: ${this.file.name}]` : '') });
        this.input = '';
        this.loading = true;

        try {
            let responseText = '';

            if (this.file) {
                const formData = new FormData();
                formData.append('file', this.file);
                try {
                    const uploadRes: any = await this.http.post('http://localhost:8000/ingest', formData).toPromise();
                    responseText += `[System]: ${uploadRes.message}\nPreview: ${uploadRes.content_preview}\n\n`;
                } catch (e) {
                    responseText += `[System]: File upload failed: ${e}\n\n`;
                }
                this.file = null;
            }

            if (userMessage) {
                const res: any = await this.http.post('http://localhost:8000/chat', { message: userMessage }).toPromise();
                responseText += res.response;
            }

            this.messages.push({ role: 'assistant', content: responseText });
        } catch (error) {
            this.messages.push({ role: 'assistant', content: 'Error: Failed to communicate with the agent.' });
        } finally {
            this.loading = false;
        }
    }
}
