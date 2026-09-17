import { Injectable } from '@angular/core';
import { HttpErrorResponse, HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from './auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private auth: AuthService, private router: Router) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const token = this.auth.getToken();
    const authReq = token
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req;

    return next.handle(authReq).pipe(
      catchError((error: unknown) => {
        // Only force a logout for a 401 on a request that actually carried a
        // token -- an expired/invalid session. A 401 on the login form
        // itself (no token attached) just means "wrong credentials" and
        // must be left for that component to show, not redirected away.
        if (token && error instanceof HttpErrorResponse && error.status === 401) {
          this.auth.logout();
          this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
        }
        return throwError(() => error);
      })
    );
  }
}
