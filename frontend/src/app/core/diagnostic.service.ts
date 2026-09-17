import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DiagnosticQuestion {
  id: number;
  lesson_id: number;
  prompt: string;
  question_type: 'single_choice' | 'multi_choice';
  choices: string[];
}

export interface DiagnosticStart {
  attempt_id: number;
  scope: 'track' | 'module';
  questions: DiagnosticQuestion[];
}

export interface DiagnosticAnswerIn {
  question_id: number;
  selected_choices: number[];
}

export interface TopicMastery {
  lesson_id: number;
  lesson_title: string;
  module_id: number;
  module_title: string;
  score: number;
  band: 'mastered' | 'partially_mastered' | 'needs_learning';
}

export interface DiagnosticResult {
  attempt_id: number;
  topic_mastery: TopicMastery[];
  recommended_start_lesson_id: number | null;
  recommended_start_lesson_title: string | null;
  recommended_start_module_id: number | null;
  recommended_start_module_title: string | null;
  auto_completed_lesson_ids: number[];
}

export interface DiagnosticStatus {
  attempt_id: number;
  submitted_at: string | null;
}

export interface Recommendation {
  recommended_start_lesson_id: number | null;
  recommended_start_lesson_title: string | null;
  recommended_start_module_id: number | null;
  recommended_start_module_title: string | null;
}

@Injectable({ providedIn: 'root' })
export class DiagnosticService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getTrackStatus(trackId: number): Observable<DiagnosticStatus | null> {
    return this.http.get<DiagnosticStatus | null>(`${this.apiUrl}/tracks/${trackId}/diagnostic/status`);
  }

  startTrackDiagnostic(trackId: number): Observable<DiagnosticStart> {
    return this.http.post<DiagnosticStart>(`${this.apiUrl}/tracks/${trackId}/diagnostic/start`, {});
  }

  startModuleDiagnostic(moduleId: number): Observable<DiagnosticStart> {
    return this.http.post<DiagnosticStart>(`${this.apiUrl}/modules/${moduleId}/diagnostic/start`, {});
  }

  submitDiagnostic(attemptId: number, answers: DiagnosticAnswerIn[]): Observable<DiagnosticResult> {
    return this.http.post<DiagnosticResult>(`${this.apiUrl}/diagnostic/attempts/${attemptId}/submit`, { answers });
  }

  getTrackRecommendation(trackId: number): Observable<Recommendation> {
    return this.http.get<Recommendation>(`${this.apiUrl}/tracks/${trackId}/recommendation`);
  }

  getTrackMastery(trackId: number): Observable<TopicMastery[]> {
    return this.http.get<TopicMastery[]>(`${this.apiUrl}/tracks/${trackId}/mastery`);
  }
}
