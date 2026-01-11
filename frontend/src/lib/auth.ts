/**
 * FAIM Lab - NextAuth Configuration
 *
 * Uses CredentialsProvider for email/password auth.
 * NO KEYCLOAK - All auth handled by our backend.
 *
 * Security:
 * - Argon2 password hashing (backend)
 * - JWT session tokens
 * - Secure cookies (HttpOnly, SameSite)
 */

import { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import jwt from "jsonwebtoken";

// Backend API URL
// For server-side (Docker): use API_HOST (internal container name)
// For client-side: use NEXT_PUBLIC_BACKEND_URL (localhost)
const API_URL = process.env.API_HOST
  ? `http://${process.env.API_HOST}`
  : process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// JWT secret for signing access tokens (must match backend JWT_SECRET)
const JWT_SECRET = process.env.NEXTAUTH_SECRET || "dev-jwt-secret-key";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      id: "credentials",
      name: "Email & Password",
      credentials: {
        email: {
          label: "Email",
          type: "email",
          placeholder: "you@example.com",
        },
        password: {
          label: "Password",
          type: "password",
        },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          // Call backend to verify credentials
          const res = await fetch(`${API_URL}/api/v1/auth/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          const data = await res.json();

          if (data.valid && data.user_id) {
            // Return user object for session
            return {
              id: data.user_id,
              email: data.email,
              name: data.name || data.email,

              graphId: data.graph_id,
            };
          }

          return null;
        } catch (error) {
          console.error("Auth error:", error);
          return null;
        }
      },
    }),
  ],

  // Use JWT sessions
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  // Custom pages
  pages: {
    signIn: "/auth/login",
    signOut: "/auth/logout",
    error: "/auth/error",
    newUser: "/dashboard",
  },

  // JWT and session callbacks
  callbacks: {
    async jwt({ token, user }) {
      // On initial sign in, persist user data to token
      if (user) {
        token.userId = user.id;
        token.email = user.email;
        token.name = user.name;

        token.graphId = (user as any).graphId;
      }
      
      // Generate accessToken for backend API calls (HS256 signed)
      // This is what the backend will verify
      token.accessToken = jwt.sign(
        {
          sub: token.userId || token.sub,
          id: token.userId || token.sub,
          email: token.email,
          name: token.name,

          graphId: token.graphId,
        },
        JWT_SECRET,
        { algorithm: "HS256", expiresIn: "30d" }
      );

      return token;
    },

    async session({ session, token }) {
      // Send user data to client session
      if (token) {
        session.user = {
          ...session.user,
          id: token.userId as string,
          email: token.email as string,
          name: token.name as string,
        };
        // Add custom properties

        (session as any).graphId = token.graphId;
        // CRITICAL: Expose accessToken for backend API calls
        (session as any).accessToken = token.accessToken;
      }
      return session;
    },
  },

  // Security
  secret: process.env.NEXTAUTH_SECRET,

  // Debug in development
  debug: process.env.NODE_ENV === "development",
};
