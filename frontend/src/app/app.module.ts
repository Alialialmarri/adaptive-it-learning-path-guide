import { ErrorHandler, NgModule } from '@angular/core';
import { GlobalErrorHandler } from './core/global-error-handler';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi, withXhr } from '@angular/common/http';
import { AuthInterceptor } from './core/auth.interceptor';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './features/auth/login.component';
import { RegisterComponent } from './features/auth/register.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { TrackMapComponent } from './features/track-map/track-map.component';
import { ChatInterfaceComponent } from './features/chat/chat-interface.component';
import { ModuleViewComponent } from './features/module-view/module-view.component';
import { NotFoundComponent } from './features/not-found/not-found.component';
import { ErrorPageComponent } from './features/error-page/error-page.component';

@NgModule({ declarations: [
        AppComponent,
        LoginComponent,
        RegisterComponent,
        DashboardComponent,
        TrackMapComponent,
        ChatInterfaceComponent,
        ModuleViewComponent,
        NotFoundComponent,
        ErrorPageComponent
    ],
    bootstrap: [AppComponent], imports: [BrowserModule,
        AppRoutingModule,
        FormsModule], providers: [
        { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
        { provide: ErrorHandler, useClass: GlobalErrorHandler },
        provideHttpClient(withXhr(), withInterceptorsFromDi())
    ] })
export class AppModule { }
