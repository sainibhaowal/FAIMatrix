/**
 * FAIMATRIX - NextAuth Configuration (Production Hardened)
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

// JWT secret
// In production, this MUST be set via environment variables.
const SIGNING_SECRET = process.env.NEXTAUTH_SECRET;

if (!SIGNING_SECRET) {
  console.error("CRITICAL: NEXTAUTH_SECRET is not defined in environment variables!");
} else {
  console.log(`[Auth] Loaded SIGNING_SECRET (len: ${SIGNING_SECRET.length})`);
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      id: "credentials",
      name: "Email & OTP",
      credentials: {
        email: { label: "Email", type: "email" },
        code: { label: "Code", type: "text" },
        full_name: { label: "Name", type: "text" }, // Support signup name passthrough
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.code) {
          console.warn("[Auth] authorize: Missing email or code");
          return null;
        }

        const verifyUrl = `${API_URL}/api/v1/auth/otp/verify`;
        console.log(`[Auth] Verifying ${credentials.email} at ${verifyUrl}...`);

        try {
          const res = await fetch(verifyUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              code: credentials.code,
              full_name: (credentials as any).full_name,
            }),
          });

          if (!res.ok) {
            const errorText = await res.text();
            console.error(`[Auth] Verification HTTP ${res.status}: ${errorText}`);
            return null;
          }

          const data = await res.json();
          
          if (data.success && data.user) {
            console.log(`[Auth] Verification SUCCESS for ${credentials.email}`);
            return {
              id: data.user.id,
              email: data.user.email,
              name: data.user.name || data.user.email,
              graphId: data.user.graph_id,
            };
          }

          console.warn(`[Auth] Verification FAILED: ${data.message || "Unknown reason"}`);
          return null;
        } catch (err: any) {
          console.error(`[Auth] Verification FETCH ERROR: ${err.message}`);
          return null;
        }
      },
    }),
  ],

  // Storage
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  // Security
  secret: SIGNING_SECRET,

  // UI
  pages: {
    signIn: "/auth/login",
    signOut: "/auth/logout",
    error: "/auth/error",
  },

  callbacks: {
    async jwt({ token, user }) {
      // 1. Persist user data to token on initial sign-in
      if (user) {
        token.userId = user.id;
        token.email = user.email;
        token.name = user.name;
        token.graphId = (user as any).graphId;
      }
      
      // 2. Generate/Rotate access token for backend API (HS256)
      if (SIGNING_SECRET) {
        try {
          token.accessToken = jwt.sign(
            {
              sub: token.userId || token.sub,
              id: token.userId || token.sub,
              email: token.email,
              name: token.name,
              graphId: token.graphId,
              type: "access",
            },
            SIGNING_SECRET,
            { algorithm: "HS256", expiresIn: "30d" }
          );
        } catch (err: any) {
          console.error(`[Auth] JWT Sign Error: ${err.message}`);
        }
      }

      return token;
    },

    async session({ session, token }) {
      if (token) {
        session.user = {
          ...session.user,
          id: token.userId as string,
          email: token.email as string,
          name: token.name as string,
        };
        (session as any).graphId = token.graphId;
        (session as any).accessToken = token.accessToken;
      }
      return session;
    },
  },

  debug: process.env.NODE_ENV === "development",
};
