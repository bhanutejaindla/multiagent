import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

@Component({
    selector: 'app-chat',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './chat.component.html',
    styleUrls: ['./chat.component.css']
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
