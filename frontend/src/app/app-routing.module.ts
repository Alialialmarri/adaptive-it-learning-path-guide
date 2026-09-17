import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login.component';
import { RegisterComponent } from './features/auth/register.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { ModuleViewComponent } from './features/module-view/module-view.component';
import { NotFoundComponent } from './features/not-found/not-found.component';
import { ErrorPageComponent } from './features/error-page/error-page.component';
import { DiagnosticAssessmentComponent } from './features/diagnostic/diagnostic-assessment.component';
import { ProfileComponent } from './features/profile/profile.component';
import { authGuard } from './core/auth.guard';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'dashboard/diagnostic', component: DiagnosticAssessmentComponent, canActivate: [authGuard] },
  { path: 'dashboard/module/:title', component: ModuleViewComponent, canActivate: [authGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [authGuard] },
  { path: 'error', component: ErrorPageComponent },
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: '**', component: NotFoundComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
