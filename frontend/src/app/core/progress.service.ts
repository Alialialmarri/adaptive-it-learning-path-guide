import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ModuleProgress {
  module_id: number;
  status: 'locked' | 'in_progress' | 'completed';
  completion_percentage: number;
  completed_lesson_ids: number[];
  last_accessed: string | null;
}

export interface ResumeModule {
  module_id: number;
  module_title: string;
  status: string;
  last_accessed: string | null;
}

@Injectable({ providedIn: 'root' })
export class ProgressService {
  private apiUrl = `${environment.apiUrl}/progress`;

  constructor(private http: HttpClient) {}

  openModule(moduleId: number): Observable<ModuleProgress> {
    return this.http.post<ModuleProgress>(`${this.apiUrl}/modules/${moduleId}/open`, {});
  }

  getModuleProgress(moduleId: number): Observable<ModuleProgress> {
    return this.http.get<ModuleProgress>(`${this.apiUrl}/modules/${moduleId}`);
  }

  setLessonCompletion(lessonId: number, completed: boolean): Observable<ModuleProgress> {
    return this.http.put<ModuleProgress>(`${this.apiUrl}/lessons/${lessonId}`, { completed });
  }

  listProgress(): Observable<ModuleProgress[]> {
    return this.http.get<ModuleProgress[]>(this.apiUrl);
  }

  resume(): Observable<ResumeModule | null> {
    return this.http.get<ResumeModule | null>(`${this.apiUrl}/resume`);
  }
}
