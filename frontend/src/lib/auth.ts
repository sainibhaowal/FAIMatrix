/**
 * FAIM Lab - NextAuth Configuration (Production Hardened)
 *
 * Uses CredentialsProvider for email/OTP auth (passwordless).
 *
 * Security Features:
 * - No passwords (OTP-only authentication)
 * - JWT session tokens (HS256 signed)
 * - Secure cookies (HttpOnly, SameSite=Lax, Secure in production)
 * - Required environment secrets (no fallbacks)
 */

import { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import jwt from "jsonwebtoken";

// Backend API URL
const API_URL = process.env.API_HOST
  ? `http://${process.env.API_HOST}`
  : process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// JWT secret - REQUIRED, no fallback for security
const JWT_SECRET = process.env.NEXTAUTH_SECRET;
if (!JWT_SECRET && process.env.NODE_ENV === "production") {
  throw new Error("NEXTAUTH_SECRET environment variable is required in production");
}
// Only allow fallback in development
const SIGNING_SECRET = JWT_SECRET || (process.env.NODE_ENV === "development" ? "dev-only-secret-not-for-production" : "");

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
        code: {
          label: "Verification Code",
          type: "text",
          placeholder: "123456",
        },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.code) {
          return null;
        }
    
        try {
          // Call backend to verify OTP code
          const res = await fetch(`${API_URL}/api/v1/auth/otp/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              code: credentials.code,
              full_name: (credentials as any).full_name,
            }),
          });
    
          const data = await res.json();
    
          if (res.ok && data.success && data.user) {
            // Return user object for session
            return {
              id: data.user.id,
              email: data.user.email,
              name: data.user.name || data.user.email,
              graphId: data.user.graph_id,
              // We could also store the backend tokens if we want to proxy them,
              // but current JWT callback generates its own for consistency with middleware.
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
          type: "access",
        },
        SIGNING_SECRET as string,
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
