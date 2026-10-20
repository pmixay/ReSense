import { createContext, useContext } from 'react';

/** Passing views are decorative: no global shortcuts, preferences or extra GPU scenes. */
export const NavigationPreviewContext = createContext(false);
export const useNavigationPreview = () => useContext(NavigationPreviewContext);
