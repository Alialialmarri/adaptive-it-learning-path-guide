import { Component, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({
    selector: 'app-error-page',
    templateUrl: './error-page.component.html',
    styleUrls: ['./error-page.component.scss'],
    changeDetection: ChangeDetectionStrategy.Eager,
    standalone: false
})
export class ErrorPageComponent {
  message: string;

  constructor(route: ActivatedRoute) {
    this.message = route.snapshot.queryParamMap.get('message')
      ?? 'Something went wrong. Please try again.';
  }
}
