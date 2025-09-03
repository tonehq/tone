import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyDj1FtO0YiO_aVN8AjfNb3nZXLd7fDVH9w",
  authDomain: "clickguides-ad196.firebaseapp.com",
  projectId: "clickguides-ad196",
  storageBucket: "clickguides-ad196.appspot.com",
  messagingSenderId: "818712143450",
  appId: "1:818712143450:web:8617a132cbb07365815a63",
};

const app = initializeApp(firebaseConfig);

const auth = getAuth(app);

export { auth, app };
