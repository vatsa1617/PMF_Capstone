import crypto from 'crypto';

const ACTIVE_TOKENS = {};
const VALID_USERS = {
  PMF_CAPSTONE: {
    password_hash: crypto.createHash('sha256').update('Virginia@1234').digest('hex'),
    description: 'Capstone Project Account'
  }
};

function hashPassword(password) {
  return crypto.createHash('sha256').update(password).digest('hex');
}

function verifyPassword(storedHash, providedPassword) {
  return storedHash === hashPassword(providedPassword);
}

function generateToken() {
  return crypto.randomBytes(32).toString('base64');
}

function createSession(userId) {
  const token = generateToken();
  ACTIVE_TOKENS[token] = {
    user_id: userId,
    created_at: new Date(),
    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000)
  };
  return token;
}

function authenticateUser(userId, password) {
  if (!VALID_USERS[userId]) {
    return { success: false, message: 'Invalid user ID or password' };
  }

  const user = VALID_USERS[userId];
  if (!verifyPassword(user.password_hash, password)) {
    return { success: false, message: 'Invalid user ID or password' };
  }

  const token = createSession(userId);
  return { success: true, token };
}

export default async (req, context) => {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : await req.json?.() || JSON.parse(req.body);
    const { user_id, password } = body;

    if (!user_id || !password) {
      return new Response(
        JSON.stringify({ error: 'User ID and password are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    }

    const result = authenticateUser(user_id, password);

    if (result.success) {
      return new Response(
        JSON.stringify({
          status: 'success',
          token: result.token,
          user_id,
          message: 'Authentication successful'
        }),
        { status: 200, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    } else {
      return new Response(
        JSON.stringify({ error: result.message }),
        { status: 401, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    }
  } catch (error) {
    console.error('Auth error:', error);
    return new Response(
      JSON.stringify({ error: 'Invalid request', details: error.message }),
      { status: 400, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
    );
  }
};
