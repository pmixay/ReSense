// О системе: ReSense for the jury on one screen — what it does and how (the pipeline as a metro line
// into the four decisions), the headline results (README «Результаты», in-sample; caveats in «?»),
// how to check it (the ROS 2 node in five commands, the web prototype, this stand's versions from
// GET /api/system), documentation links and the team.
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
            <Chip variant="outline">команда «Молоток»</Chip>
            {sys && <Chip variant="outline">детектор {fmtVersion(sys.detector_version)}</Chip>}
          </>
        }
        actions={
          <>
            <Button variant="outline" icon="info" iconRight="external" href={GUIDE_URL} target="_blank">
              Руководство
            </Button>
            <Button variant="primary" icon="sparkle" to="/upload?source=demo">
              Попробовать на демо
            </Button>
          </>
        }
      />
      <section className={`grid-12 fill-viewport ${styles.about}`}>
        <HowCard />
        <Results />
        <div className={styles.bottom}>
          <RosCard />
          <WebCard system={system} />
          <LinksCard />
          <TeamCard />
        </div>
      </section>
    </>
  );
}
