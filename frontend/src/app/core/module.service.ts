import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Lesson {
  id: number;
  module_id: number;
  title: string;
  content: string;
  order: number;
}

export interface Module {
  id: number;
  title: string;
  content: string;
  order: number;
  policy?: string;
  lessons: Lesson[];
}

@Injectable({
  providedIn: 'root'
})
export class ModuleService {
  private apiUrl = `${environment.apiUrl}/modules`;

  constructor(private http: HttpClient) { }

  listModules(): Observable<Module[]> {
    return this.http.get<Module[]>(this.apiUrl);
  }

  getModule(id: number): Observable<Module> {
    return this.http.get<Module>(`${this.apiUrl}/${id}`);
  }

  getModuleByTitle(title: string): Observable<Module> {
    return this.http.get<Module>(`${this.apiUrl}/title/${title}`);
  }
}
