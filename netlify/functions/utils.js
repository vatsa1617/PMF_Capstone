const ACTIVE_TOKENS = {};

export function validateToken(token) {
  if (!ACTIVE_TOKENS[token]) {
    return null;
  }

  const session = ACTIVE_TOKENS[token];

  if (new Date() > session.expires_at) {
    delete ACTIVE_TOKENS[token];
    return null;
  }

  return session;
}

export function createSession(userId) {
  const token = require('crypto').randomBytes(32).toString('base64');
  ACTIVE_TOKENS[token] = {
    user_id: userId,
    created_at: new Date(),
    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000)
  };
  return token;
}

export function requireAuth(req) {
  const authHeader = req.headers?.get?.('Authorization') || req.headers?.['authorization'];

  if (!authHeader) {
    return {
      error: 'Missing authorization header',
      status: 401
    };
  }

  try {
    const token = authHeader.split(' ')[1];
    const session = validateToken(token);

    if (!session) {
      return {
        error: 'Invalid or expired token',
        status: 401
      };
    }

    return { session, error: null };
  } catch (error) {
    console.error('Auth error:', error);
    return {
      error: 'Invalid authorization header',
      status: 401
    };
  }
}

export function corsHeaders() {
  return {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };
}
