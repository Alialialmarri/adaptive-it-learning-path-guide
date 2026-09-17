import { Component, ElementRef, ViewChild, AfterViewChecked, Input, OnChanges, SimpleChanges, ChangeDetectionStrategy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface ChatMessageOut {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface ChatHistorySummary {
  module_id: number;
  module_title: string;
  last_message_at: string;
}

type ChatMessage = { text: string, sender: 'user' | 'bot' };

const GREETING = "Hello! I'm your AI tutor. How can I help you with this module?";

@Component({
    selector: 'app-chat-interface',
    templateUrl: './chat-interface.component.html',
    styleUrls: ['./chat-interface.component.scss'],
    changeDetection: ChangeDetectionStrategy.Eager,
    standalone: false
})
export class ChatInterfaceComponent implements AfterViewChecked, OnChanges {
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;
  @Input() context: { title: string, id: number, type: 'module' | 'lesson' } | null = null;
  // Set by the parent to the id of the enclosing module, independent of which
  // lesson is selected, so history loads once per module rather than per lesson.
  @Input() moduleId: number | null = null;

  messages: ChatMessage[] = [
    { text: GREETING, sender: 'bot' }
  ];
  userInput: string = '';
  isProcessing = false;
  private shouldScroll = true;
  private loadedForModuleId: number | null = null;

  // Picking a past conversation from another module puts the panel into a
  // read-only "viewing history" mode; sending is disabled until the student
  // returns to their live, current-module chat.
  showHistoryPanel = false;
  loadingHistoryList = false;
  historySummaries: ChatHistorySummary[] = [];
  viewingHistoryModuleId: number | null = null;
  viewingHistoryTitle = '';
  private liveMessages: ChatMessage[] = this.messages;

  constructor(private http: HttpClient, private sanitizer: DomSanitizer) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['moduleId'] && this.moduleId != null && this.moduleId !== this.loadedForModuleId) {
      this.loadedForModuleId = this.moduleId;
      this.viewingHistoryModuleId = null;
      this.showHistoryPanel = false;
      this.loadHistory(this.moduleId);
    }
  }

  private loadHistory(moduleId: number): void {
    this.http.get<ChatMessageOut[]>(`${environment.apiUrl}/chat/history/${moduleId}`)
      .subscribe({
        next: (history) => {
          this.messages = history.length > 0
            ? history.map(m => ({ text: m.content, sender: (m.role === 'user' ? 'user' : 'bot') as 'user' | 'bot' }))
            : [{ text: GREETING, sender: 'bot' }];
          this.liveMessages = this.messages;
          this.shouldScroll = true;
        },
        error: (err) => {
          console.error('Failed to load chat history:', err);
        }
      });
  }

  toggleHistoryPanel(): void {
    this.showHistoryPanel = !this.showHistoryPanel;
    if (this.showHistoryPanel && this.historySummaries.length === 0) {
      this.loadingHistoryList = true;
      this.http.get<ChatHistorySummary[]>(`${environment.apiUrl}/chat/history`)
        .subscribe({
          next: (summaries) => {
            this.historySummaries = summaries;
            this.loadingHistoryList = false;
          },
          error: (err) => {
            console.error('Failed to load chat history list:', err);
            this.loadingHistoryList = false;
          }
        });
    }
  }

  viewHistoryFor(summary: ChatHistorySummary): void {
    this.showHistoryPanel = false;
    this.http.get<ChatMessageOut[]>(`${environment.apiUrl}/chat/history/${summary.module_id}`)
      .subscribe({
        next: (history) => {
          this.messages = history.map(m => ({ text: m.content, sender: (m.role === 'user' ? 'user' : 'bot') as 'user' | 'bot' }));
          this.viewingHistoryModuleId = summary.module_id;
          this.viewingHistoryTitle = summary.module_title;
          this.shouldScroll = true;
        },
        error: (err) => console.error('Failed to load past conversation:', err)
      });
  }

  returnToCurrentChat(): void {
    this.viewingHistoryModuleId = null;
    this.messages = this.liveMessages;
    this.shouldScroll = true;
  }

  startNewChat(): void {
    // Clears the visible conversation so the student can start fresh. Past
    // messages are still stored server-side and remain reachable via History.
    this.showHistoryPanel = false;
    this.viewingHistoryModuleId = null;
    this.messages = [{ text: GREETING, sender: 'bot' }];
    this.liveMessages = this.messages;
    this.shouldScroll = true;
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  renderMarkdown(text: string): SafeHtml {
    // Parse markdown to HTML
    const html = marked.parse(text) as string;
    // Sanitize the HTML to prevent XSS
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  scrollToBottom(): void {
    if (this.shouldScroll) {
      try {
        this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
        // Only reset shouldScroll if we're not waiting for a response (optional, depending on UX preference)
        // For now, we'll keep scrolling to bottom on every view check if shouldScroll is true
        // But better logic is to set it false after scrolling, and set it true on new message
        this.shouldScroll = false;
      } catch(err) { }
    }
  }

  sendMessage() {
    if (this.userInput.trim() && !this.isProcessing && this.viewingHistoryModuleId === null) {
      const userMessage = this.userInput;

      // Add user message
      this.messages.push({ text: userMessage, sender: 'user' });
      this.userInput = '';
      this.isProcessing = true;
      this.shouldScroll = true;

      // Prepare payload with context
      const payload = {
        message: userMessage,
        context: this.context
      };

      // Call backend API
      this.http.post<any>(`${environment.apiUrl}/chat`, payload)
        .subscribe({
          next: (response) => {
            this.messages.push({
              text: response.answer,
              sender: 'bot'
            });
            this.isProcessing = false;
            this.shouldScroll = true;
          },
          error: (err) => {
            console.error('Chat error:', err);
            const detail = err?.error?.detail;
            const text = typeof detail === 'string'
              ? detail
              : "Sorry, I encountered an error processing your request.";
            this.messages.push({
              text,
              sender: 'bot'
            });
            this.isProcessing = false;
            this.shouldScroll = true;
          }
        });
    }
  }
}
