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

// Base query with authentication
const baseQuery = fetchBaseQuery({
  baseUrl: '/api',
  credentials: 'include', // Include cookies for httpOnly session
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.accessToken;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  },
});

// API slice
export const api = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['User', 'Settings'],
  endpoints: (builder) => ({
    // Auth endpoints
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

    // User endpoints
    getCurrentUser: builder.query<User, void>({
      query: () => '/v1/user',
      providesTags: ['User'],
    }),

    getUserSettings: builder.query<any, { category?: string }>({
      query: ({ category }) => ({
        url: '/v1/user/settings',
        params: category ? { category } : undefined,
      }),
      providesTags: ['Settings'],
    }),

    updateUserSettings: builder.mutation<any, { category: string; data: any; expectedVersion?: number }>({
      query: ({ category, data, expectedVersion }) => ({
        url: `/v1/user/settings/${category}`,
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
  useGetCurrentUserQuery,
  useGetUserSettingsQuery,
  useUpdateUserSettingsMutation,
} = api;