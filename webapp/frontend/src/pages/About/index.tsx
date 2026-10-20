// A readable introduction; measurements, launch instructions and team detail open on demand.
import { useSystem } from '../../api/hooks';
import { Button, Chip, PageHeader } from '../../components';
import { GUIDE_URL, fmtVersion } from './content';
import { HowCard } from './HowCard';
import { LinksCard, Results, TeamCard } from './Parts';
import { RosCard, WebCard } from './QuickStart';
import styles from './About.module.css';

export default function About() {
  const system = useSystem();
  const sys = system.isError ? undefined : system.data;
  return (
    <>
      <PageHeader
        title="О системе"
        station={3}
        chips={
          <>
            {sys && <Chip variant="outline">детектор {fmtVersion(sys.detector_version)}</Chip>}
          </>
        }
        actions={
          <>
            <Button variant="outline" href={GUIDE_URL} target="_blank">
              Руководство
            </Button>
            <Button variant="primary" to="/upload?source=demo">
              Попробовать на демо
            </Button>
          </>
        }
      />
      <div className={styles.about} data-about-workspace>
        <HowCard />
        <div className={styles.reference}>
          <Results />
          <RosCard />
          <WebCard system={system} />
          <TeamCard />
        </div>
        <LinksCard />
      </div>
    </>
  );
}
