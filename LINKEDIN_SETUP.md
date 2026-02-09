# 🔗 LinkedIn Setup Guide for MediaSnap

This guide will help you set up LinkedIn support in MediaSnap to download content from LinkedIn profiles and company pages.

## ⚠️ Important Disclaimers

**READ CAREFULLY BEFORE PROCEEDING:**

- **Terms of Service**: Using automated tools to access LinkedIn **violates LinkedIn's Terms of Service**
- **Account Risk**: Your LinkedIn account may be **restricted, suspended, or permanently banned**
- **Legal Risk**: LinkedIn has taken legal action against automated scraping services in the past
- **Use at Your Own Risk**: The MediaSnap developers are not responsible for any consequences
- **Unofficial Library**: This uses the `linkedin-api` package, which is not endorsed by LinkedIn
- **No Warranty**: This feature is provided "as-is" with no guarantees

**We strongly recommend:**
- Using a test/secondary LinkedIn account
- Limiting downloads to publicly available content
- Respecting rate limits and being courteous
- Reading LinkedIn's Terms of Service before proceeding

Only continue if you understand and accept these risks.

---

## 📋 Prerequisites

- Python 3.10 or higher
- MediaSnap installed and working
- A LinkedIn account (preferably a test account)
- Internet connection

---

## 🚀 Quick Setup

### 1. Install Dependencies

The linkedin-api library should be installed automatically with MediaSnap requirements:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install linkedin-api
```

### 2. Authenticate with LinkedIn

Run the LinkedIn login script:

```bash
python scripts/linkedin_login.py
```

Or:

```bash
cd scripts
./linkedin_login.py
```

Follow the prompts:
1. Read and accept the warnings
2. Enter your LinkedIn email address
3. Enter your LinkedIn password (input is hidden)
4. Wait for authentication to complete

If successful, your session will be saved to `~/.mediasnap/linkedin_session.pkl`.

### 3. Start Using MediaSnap

Run MediaSnap:

```bash
python app.py
```

Enter a LinkedIn URL in the input field:
- **Profile**: `https://www.linkedin.com/in/username`
- **Company**: `https://www.linkedin.com/company/companyname`

Click "Fetch Profile" to start downloading.

---

## 📂 What Gets Downloaded

### For Profiles (`/in/username`)

MediaSnap will download:
- ✅ **Profile Information**: Bio, headline, experience, education (saved as JSON)
- ✅ **Posts**: Text posts, articles, and updates
- ✅ **Articles**: Long-form LinkedIn articles
- ✅ **Media**: Images, videos, and documents shared in posts
- ✅ **Documents**: PDFs and other attachments

### For Company Pages (`/company/companyname`)

MediaSnap will download:
- ✅ **Company Information**: About, industry, size, location (saved as JSON)
- ✅ **Updates**: Company posts and announcements
- ✅ **Media**: Images and videos from posts
- ✅ **Documents**: PDFs and other shared files

---

## 📁 Download Organization

Downloads are organized as follows:

```
downloads/
└── linkedin/
    ├── username/              # Profile downloads
    │   ├── profile_info.json  # Profile data
    │   ├── posts/             # Post content (JSON + images)
    │   ├── articles/          # LinkedIn articles
    │   ├── videos/            # Video content
    │   └── documents/         # PDFs and files
    │
    └── companyname/           # Company downloads
        ├── company_info.json  # Company data
        ├── posts/             # Company updates
        ├── videos/            # Video content
        └── documents/         # PDFs and files
```

---

## 🔧 Troubleshooting

### Authentication Failed

**Problem**: "Authentication failed" error

**Solutions**:
1. **Check credentials**: Make sure email and password are correct
2. **Login via browser first**: Go to linkedin.com and log in normally
3. **Clear sessions**: Delete `~/.mediasnap/linkedin_session.pkl` and try again
4. **Security challenge**: LinkedIn may require verification (check your email)
5. **Rate limiting**: Wait 24 hours if you've made too many attempts

### "linkedin-api not installed"

**Problem**: Import error for linkedin_api

**Solution**:
```bash
pip install linkedin-api
```

### Challenge/Verification Required

**Problem**: LinkedIn asks for security verification

**Solutions**:
1. Complete the verification challenge in your browser
2. Wait 10-15 minutes for LinkedIn to clear the challenge
3. Try running the login script again
4. Consider using a different IP address (VPN) if challenges persist

### Limited Content Downloaded

**Problem**: Not all content is being downloaded

**Possible causes**:
- Content may be private/restricted
- LinkedIn API limits what can be accessed
- Rate limiting kicked in (LinkedIn throttles requests)
- Network issues during download

**Solutions**:
- Make sure the target profile/company is public
- Wait and try again later
- Check MediaSnap logs for specific errors

### Account Locked/Restricted

**Problem**: LinkedIn locked your account

**This is the main risk we warned about.**

If your account gets locked:
1. Follow LinkedIn's account recovery process
2. You may need to verify your identity
3. Consider using a different account in the future
4. Limit download frequency to avoid detection

---

## 🎯 Best Practices

### 1. Use Responsibly
- Download only publicly available content
- Respect copyright and content ownership
- Don't redistribute downloaded content without permission

### 2. Avoid Detection
- Use delays between downloads (built into MediaSnap)
- Don't download large amounts at once
- Space out your downloads over time
- Consider using a VPN

### 3. Protect Your Account
- Use a separate test account if possible
- Don't use your primary professional LinkedIn account
- Enable two-factor authentication
- Monitor your account for warnings

### 4. Data Privacy
- Your credentials are stored locally in `~/.mediasnap/linkedin_session.pkl`
- File has restricted permissions (owner read/write only)
- Delete the session file if you're done using the feature
- Never share your session file with others

---

## 🔒 Security Notes

### Credential Storage

Your LinkedIn credentials are stored in:
```
~/.mediasnap/linkedin_session.pkl
```

- File is encrypted using Python's pickle format
- File permissions are set to `0600` (owner read/write only)
- Password is stored to maintain the session
- Delete this file to remove stored credentials

To delete:
```bash
rm ~/.mediasnap/linkedin_session.pkl
```

### Session Management

- Sessions typically last 1-2 weeks
- You may need to re-authenticate periodically
- If authentication fails, run `scripts/linkedin_login.py` again

---

## ❓ FAQ

### Q: Is this legal?

**A**: It's a gray area. LinkedIn's ToS prohibit automated scraping, but courts have ruled that scraping publicly available data may be legal. However, LinkedIn actively enforces their ToS and may restrict accounts. **Use at your own risk.**

### Q: Will my account get banned?

**A**: Possibly. LinkedIn actively combats scraping and may restrict accounts that exhibit automated behavior. Use a test account to minimize risk.

### Q: Can I download private profiles?

**A**: No. You can only download content that's visible to your account when logged in normally. If you can't see it in a browser, MediaSnap can't download it.

### Q: How much can I download?

**A**: There's no specific limit, but LinkedIn rate-limits API requests. Aggressive downloading will trigger rate limits or account restrictions. Be conservative.

### Q: Does MediaSnap store my password?

**A**: Yes, it's stored locally in `~/.mediasnap/linkedin_session.pkl` to maintain your session. The file has restricted permissions. You can delete it anytime.

### Q: Can I use this for commercial purposes?

**A**: **NO.** This violates LinkedIn's Terms of Service. This tool is for personal archival use only.

---

## 📞 Support

If you encounter issues:

1. Check this guide for troubleshooting steps
2. Review MediaSnap logs: `logs/mediasnap.log`
3. Check the [main README](../README.md) for general help
4. Open an issue on GitHub (but read disclaimers first!)

---

## 🙏 Acknowledgments

- [linkedin-api](https://github.com/tomquirk/linkedin-api) - Unofficial LinkedIn API library
- LinkedIn users who shared their experiences with automation

---

<div align="center">

**⚠️ Use Responsibly • Respect Terms of Service • Protect Your Account ⚠️**

</div>
