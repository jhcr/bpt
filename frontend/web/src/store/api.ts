// RTK Query API configuration with authentication
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { RootState } from './index';

export interface User {
  id: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  settings: Record<string, any>;
}

export interface LoginRequest {
  username: string;
  password?: string;
  cipher_envelope?: {
    client_public_key_jwk: JsonWebKey;
    nonce: string;
    password_enc: string;
    sid: string;
  };
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface SessionResponse {
  sid: string;
  server_public_key_jwk: JsonWebKey;
}

export interface SignupRequest {
  email: string;
  password: string;
  given_name?: string;
  family_name?: string;
  phone_number?: string;
}

export interface SignupResponse {
  message: string;
  requires_confirmation: boolean;
}

export interface SocialProvider {
  name: string;
  display_name: string;
  authorization_url: string;
}

export interface SocialProvidersResponse {
  providers: SocialProvider[];
}

export interface OAuthAuthorizeResponse {
  authorization_url: string;
  state: string;
  provider: string;
}

// Base query with authentication - connects to BFF service via proxy
const baseQuery = fetchBaseQuery({
  baseUrl: '/',
  credentials: 'include', // Include cookies for httpOnly session
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.accessToken;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    headers.set('Content-Type', 'application/json');
    return headers;
  },
});

// API slice
export const api = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['User', 'Settings'],
  endpoints: (builder) => ({
    // Auth endpoints (proxied to auth service)
    createSession: builder.mutation<SessionResponse, void>({
      query: () => ({
        url: '/auth/session',
        method: 'POST',
        body: {},
      }),
    }),

    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
    }),

    logout: builder.mutation<void, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
    }),

    refresh: builder.mutation<LoginResponse, void>({
      query: () => ({
        url: '/auth/refresh',
        method: 'POST',
      }),
    }),

    signup: builder.mutation<SignupResponse, SignupRequest>({
      query: (data) => ({
        url: '/auth/signup',
        method: 'POST',
        body: data,
      }),
    }),

    // OAuth endpoints
    getSocialProviders: builder.query<SocialProvidersResponse, void>({
      query: () => '/auth/social/providers',
    }),

    getOAuthAuthorizeUrl: builder.query<OAuthAuthorizeResponse, { provider: string; redirectAfterLogin?: string }>({
      query: ({ provider, redirectAfterLogin }) => ({
        url: `/auth/social/${provider}/authorize`,
        params: redirectAfterLogin ? { redirect_after_login: redirectAfterLogin } : undefined,
      }),
    }),

    // User endpoints (via BFF service)
    getCurrentUser: builder.query<User, void>({
      query: () => '/api/v1/user',
      providesTags: ['User'],
    }),

    getUserSettings: builder.query<any, { category?: string }>({
      query: ({ category }) => ({
        url: '/api/v1/user/settings',
        params: category ? { category } : undefined,
      }),
      providesTags: ['Settings'],
    }),

    updateUserSettings: builder.mutation<any, { category: string; data: any; expectedVersion?: number }>({
      query: ({ category, data, expectedVersion }) => ({
        url: `/api/v1/user/settings/${category}`,
        method: 'PUT',
        body: {
          data,
          expected_version: expectedVersion,
        },
      }),
      invalidatesTags: ['Settings', 'User'],
    }),
  }),
});

export const {
  useCreateSessionMutation,
  useLoginMutation,
  useLogoutMutation,
  useRefreshMutation,
  useSignupMutation,
  useGetSocialProvidersQuery,
  useGetOAuthAuthorizeUrlQuery,
  useGetCurrentUserQuery,
  useGetUserSettingsQuery,
  useUpdateUserSettingsMutation,
} = api;