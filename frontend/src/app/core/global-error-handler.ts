import { ErrorHandler, Injectable, Injector } from '@angular/core';
import { Router } from '@angular/router';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  constructor(private injector: Injector) {}

  handleError(error: unknown): void {
    console.error('Unhandled error:', error);
    const router = this.injector.get(Router);
    const message = error instanceof Error ? error.message : 'An unexpected error occurred.';
    router.navigate(['/error'], { queryParams: { message } });
  }
}
